import tkinter as tk
from test_0116_A import RobotMain
from xarm.wrapper import XArmAPI
import speech_recognition as sr
from threading import Thread
import json
import google.generativeai as genai
from gtts import gTTS
from playsound import playsound

API_KEY="Your KEY"
genai.configure(api_key=API_KEY)
r = sr.Recognizer()
generation_config=genai.GenerationConfig(temperature=1,response_mime_type="application/json")
model=genai.GenerativeModel('gemini-1.5-flash',generation_config=generation_config)
class GUI:
    def __init__(self):
    
        self.root = tk.Tk()
        self.root.title("아이스크림 토핑 선택")
        self.root.geometry("300x400")
        
        self.topping_sequence = []  # 선택된 토핑 순서를 저장
        self.text = ""  # 음성 인식 텍스트
        self.listening = False  # 음성 인식 상태
        
        # 메인 프레임 생성
        main_frame = tk.Frame(self.root)
        main_frame.pack(pady=20)

        # 토핑 추가 버튼 및 체크박스 생성
        self.create_topping_options(main_frame)

        # 주문 버튼 생성
        order_btn = tk.Button(self.root, text="주문", command=self.order)
        order_btn.pack(pady=10)

        # 음성 인식 버튼 생성
        self.btn_text = tk.StringVar(value="음성 시작")
        voice_btn = tk.Button(self.root, textvariable=self.btn_text, command=self.toggle_listening, font=("Arial", 16))
        voice_btn.pack(pady=20)

        # 버리기 버튼 생성
        discard_btn = tk.Button(self.root, text="버리기", command=self.discard_action, font=("Arial", 16), bg="red", fg="white")
        discard_btn.pack(pady=20)

        self.root.mainloop()
    
    def speak(self,text):
        file_name='voice.mp3'
        tts=gTTS(text=text, lang='ko')
        tts.save(file_name)
        playsound(file_name)
    def create_topping_options(self, parent_frame):
        # 토핑 라디오 버튼 (중복 선택 불가)
        toppings = ["A", "B", "C", "N"]
        for topping in toppings:
            frame = tk.Frame(parent_frame)
            frame.pack(anchor="w", pady=5)

            # 각 토핑 추가 버튼
            add_btn = tk.Button(frame, text=f"{topping} 추가", command=lambda t=topping: self.add_topping(t))
            add_btn.pack(side="left", padx=10)

    def add_topping(self, topping):
        self.topping_sequence.append(topping)
        print(f"현재 토핑 순서: {''.join(self.topping_sequence)}")
    
    def toggle_listening(self):
        if self.listening:
            # 음성 정지
            self.listening = False
            self.btn_text.set("음성 시작")
            print(f"최종 텍스트: {self.text}")
        else:
            # 음성 시작
            self.listening = True
            self.btn_text.set("음성 정지")
            # 음성 인식을 별도 스레드에서 실행
            thread = Thread(target=self.start_listening)
            thread.daemon = True
            thread.start()

    def start_listening(self):
        self.speak('무엇을 도와 드릴까요?')
        with sr.Microphone() as source:
            print("듣고 있어요...")
            while self.listening:
                try:
                    audio = r.listen(source, timeout=20, phrase_time_limit=30)
                    recognized_text = r.recognize_google(audio, language='ko')
                    self.text += recognized_text
                    print(f"인식된 텍스트: {recognized_text}")
                except sr.UnknownValueError:
                    print("인식 실패")
                except sr.RequestError as e:
                    print(f"요청 실패: {e}")
                except Exception as ex:
                    print(f"예상치 못한 오류: {ex}")
    def discard_action(self):
        arm = XArmAPI('192.168.1.184', baud_checkset=False)
        robot_main = RobotMain(arm,"C")
        robot_main.Trash_Throw()

    def summarize_order(self):
        if not self.topping_sequence:
            print("선택된 토핑이 없습니다!")
            self.speak("선택된 토핑이 없습니다")
            return
        else:
            # A, B, C, N을 토핑 이름으로 매핑
            topping_names = {"A": "딸기", "B": "복숭아", "C": "초코", "N": "토핑없음"}
            topping_counts = {"A": 0, "B": 0, "C": 0, "N": 0}

            # 토핑 개수 계산
            for topping in self.topping_sequence:
                topping_counts[topping] += 1

            # 결과 문자열 생성
            result = []
            for key, count in topping_counts.items():
                if count > 0 and key != "N":  # N은 제외하고 출력
                    result.append(f"{topping_names[key]} 토핑 {count}개")

            # 최종 메시지 출력
            if result:
                print(f"당신은 {', '.join(result)} 주문하였습니다.")
                text=f"당신은 {', '.join(result)} 주문하였습니다."
                self.speak(text)
            else:
                print("모든 토핑이 '토핑없음'으로 선택되었습니다.")
                text="모든 토핑이 '토핑없음'으로 선택되었습니다."
                self.speak(text)
    def order(self):
        if self.text!='':
            generation_config=genai.GenerationConfig(temperature=1,response_mime_type="application/json")
            model=genai.GenerativeModel('gemini-2.0-flash-exp',generation_config=generation_config)
            print("주문된 텍스트:")
            self.text+='여기에 각 토핑이 몇개씩 들어있는지 말해줘 딸기, 초코, 복숭아토핑이 없으면 0으로 해줘  '
            self.text+='혹시 텍스트에서 오류가 있을 수도 있으니 알아서 딸기, 복숭아, 초코,토핑없음으로 분류해서 토핑개수 말해줘 한국어로'
            self.text+='답장형식의 딕셔너리 키는 오직 "딸기", "복숭아","초코", "토핑없음" 만있게 해줘'
            #self.text+='토핑추가 없이 개수만 말하면 "토핑없음":count 로 알려줘. 이것도 없으면 0으로 말해줘'
            self.text+='복숭아랑 토핑없음을 계속 헷갈리는데 이거 고쳐서 정확히 답해줘'
            response=model.generate_content("""
            이 JSON 스키마를 사용해서, Order={"topping_name": count} 형태로만 출력하세요.
            텍스트나 설명 없이 JSON 딕셔너리만 반환하세요.
            
            """)
            
            response=model.generate_content(self.text)
            print(response.text)
            self.text=''
            try:
                order = json.loads(response.text)
                print("Parsed JSON:", order)
                output_string = ""
                key_to_char = {"딸기": "A", "복숭아": "B", "초코": "C", "토핑없음": "N"}
                # 개수만큼 반복하여 문자열 생성
                for key, count in order.items():
                    output_string += key_to_char.get(key, "") * int(count)
                
                print("Formatted Output:", output_string)
                self.topping_sequence=list(output_string)
            except json.JSONDecodeError as e:
                print("JSONDecodeError:", e)
                print("Response text was not valid JSON:", response.text)
        if not self.topping_sequence:
            print("선택해주세요!")
            return
        self.topping_sequence.sort()
        self.summarize_order()
        print(f"최종 토핑 순서: {''.join(self.topping_sequence)}")
        for topping in self.topping_sequence:
            arm = XArmAPI('192.168.1.184', baud_checkset=False)
            robot_main = RobotMain(arm,topping)
            robot_main.run()
        self.topping_sequence = []

if __name__ == "__main__":
    GUI()
