import tkinter as tk
from tkinter import messagebox
from datetime import datetime
import mysql.connector

from RBlibrary import RobotMain
from xarm.wrapper import XArmAPI




"""
25.01.21

로봇 제어 이식 완료

음성인식 빼고 다 됨

"""


# MySQL 데이터베이스 연결
def connect_to_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="password",
        database="test_DB_1"
    )


class IceCreamOrderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ice Cream Order")
        self.root.geometry("400x650")

        self.orders = []  # 주문 내역을 저장하는 큐
        self.trash = []  # 쓰레기통 역할 리스트

        # Flavor selection
        self.flavor_label = tk.Label(root, text="Flavor:")
        self.flavor_label.pack(anchor="w", padx=10, pady=5)

        self.flavor_var = tk.StringVar()

        self.Blueberry_button = tk.Radiobutton(root, text="Blueberry", variable=self.flavor_var, value="Blueberry")
        self.Blueberry_button.pack(anchor="w", padx=20)

        self.Strawberry_button = tk.Radiobutton(root, text="Strawberry", variable=self.flavor_var, value="Strawberry")
        self.Strawberry_button.pack(anchor="w", padx=20)

        # Topping selection
        self.topping_label = tk.Label(root, text="Topping:")
        self.topping_label.pack(anchor="w", padx=10, pady=5)

        self.topping_var = tk.StringVar()

        self.Tropical_button = tk.Radiobutton(root, text="Tropical", variable=self.topping_var, value="Tropical")
        self.Tropical_button.pack(anchor="w", padx=20)

        self.Chocoring_button = tk.Radiobutton(root, text="Chocoring", variable=self.topping_var, value="Chocoring")
        self.Chocoring_button.pack(anchor="w", padx=20)

        self.Cereal_button = tk.Radiobutton(root, text="Cereal", variable=self.topping_var, value="Cereal")
        self.Cereal_button.pack(anchor="w", padx=20)

        # Buttons
        self.continue_button = tk.Button(root, text="장바구니 추가", command=self.add_order)
        self.continue_button.pack(pady=10)

        self.complete_button = tk.Button(root, text="주문하기", command=self.complete_order)
        self.complete_button.pack(pady=10)

        self.process_button = tk.Button(root, text="처리 완료", command=self.process_order, state=tk.DISABLED)
        self.process_button.pack(pady=10)

        self.trash_button = tk.Button(root, text="쓰레기 버리기", command=self.move_to_trash)
        self.trash_button.pack(pady=10)

        self.clear_trash_button = tk.Button(root, text="쓰레기 완료", command=self.clear_trash)
        self.clear_trash_button.pack(pady=10)

        self.popular_menu_button = tk.Button(root, text="인기 메뉴 보이기", command=self.show_popular_items)
        self.popular_menu_button.pack(pady=10)

        self.voice_order_button = tk.Button(root, text="음성인식 주문하기", command=self.voice_order)
        self.voice_order_button.pack(pady=10)

        # Current order display
        self.current_order_label = tk.Label(root, text="현재 주문:", font=("Arial", 14))
        self.current_order_label.pack(pady=10)

        self.current_order_text = tk.Label(root, text="없음", font=("Arial", 12))
        self.current_order_text.pack(pady=5)

    def add_order(self):
        selected_flavor = self.flavor_var.get()
        selected_topping = self.topping_var.get()

        if not selected_flavor or not selected_topping:
            messagebox.showerror("Error", "Please select both a flavor and a topping.")
            return

        self.orders.append((selected_flavor, selected_topping))
        self.flavor_var.set(None)
        self.topping_var.set(None)

    def complete_order(self):
        if not self.orders:
            messagebox.showerror("Error", "Please add at least one order before completing.")
            return

        self.save_orders_to_db() # DB에 저장
        self.update_current_order()
        self.process_button.config(state=tk.NORMAL)


    def save_orders_to_db(self):
        try:
            conn = connect_to_db()
            cursor = conn.cursor()

            # 사용자 추가 (현재 임의 사용자 추가)
            cursor.execute("INSERT INTO users (created_at) VALUES (%s)", (datetime.now(),))
            conn.commit()
            user_id = cursor.lastrowid

            # orders 테이블에 추가
            cursor.execute("INSERT INTO orders (user_id) VALUES (%s)", (user_id,))
            conn.commit()

            order_id = cursor.lastrowid

            # order_items 테이블에 추가
            for flavor, topping in self.orders:
                cursor.execute("SELECT ice_cream_id FROM ice_cream WHERE flavor_name = %s", (flavor,))
                ice_cream_id = cursor.fetchone()

                cursor.execute("SELECT topping_id FROM toppings WHERE topping_name = %s", (topping,))
                topping_id = cursor.fetchone()

                if ice_cream_id and topping_id:
                    cursor.execute(
                        "INSERT INTO order_items (order_id, ice_cream_id, topping_id, is_processed) VALUES (%s, %s, %s, %s)",
                        (order_id, ice_cream_id[0], topping_id[0], 0)
                    )

            conn.commit()
            conn.close()

            messagebox.showinfo("Success", "Order has been completed successfully!")
        except Exception as e:
            messagebox.showerror("Database Error", f"An error occurred: {e}")
    

    def process_order(self):

        
        current_order = self.orders[0]  # 현재 주문만 처리
        flavor, topping = current_order
        self.send_to_robot(mode="ice_cream", flavor=flavor, topping=topping)
        
        if not self.orders:
            messagebox.showerror("Error", "No orders to process.")
            return

        try:
            conn = connect_to_db()
            cursor = conn.cursor()

            # Update the is_processed flag for the current order
            cursor.execute(
                "UPDATE order_items SET is_processed = 1 WHERE order_id = (SELECT order_id FROM orders ORDER BY order_id DESC LIMIT 1) AND is_processed = 0 LIMIT 1"
            )
            conn.commit()
            conn.close()

            self.orders.pop(0)

            if self.orders:
                self.update_current_order()
            else:
                self.current_order_text.config(text="없음")
                self.process_button.config(state=tk.DISABLED)

            messagebox.showinfo("Success", "Order processed successfully!")
        except Exception as e:
            messagebox.showerror("Database Error", f"An error occurred: {e}")


    def move_to_trash(self):
        # 로봇에 쓰레기 이동 명령 전송
        self.send_to_robot(mode="trash_disposal")

        if self.orders:
            self.update_current_order()
        else:
            self.current_order_text.config(text="없음")
            self.process_button.config(state=tk.DISABLED)

    def clear_trash(self):
        self.trash.clear()
        messagebox.showinfo("Info", "Trash cleared successfully.")
        

    def show_popular_items(self):
        try:
            conn = connect_to_db()
            cursor = conn.cursor()

            # 가장 인기 있는 맛 조회
            query_flavor = """
            SELECT ic.flavor_name, COUNT(*) AS count
            FROM order_items oi
            JOIN ice_cream ic ON oi.ice_cream_id = ic.ice_cream_id
            GROUP BY ic.flavor_name
            ORDER BY count DESC
            LIMIT 1;
            """
            cursor.execute(query_flavor)
            popular_flavor = cursor.fetchone()

            # 가장 인기 있는 토핑 조회
            query_topping = """
            SELECT t.topping_name, COUNT(*) AS count
            FROM order_items oi
            JOIN toppings t ON oi.topping_id = t.topping_id
            GROUP BY t.topping_name
            ORDER BY count DESC
            LIMIT 1;
            """
            cursor.execute(query_topping)
            popular_topping = cursor.fetchone()

            conn.close()

            if popular_flavor and popular_topping:
                messagebox.showinfo(
                    "Popular Items",
                    f"인기 있는 맛: {popular_flavor[0]} ({popular_flavor[1]}번 주문됨)\n"
                    f"인기 있는 토핑: {popular_topping[0]} ({popular_topping[1]}번 주문됨)"
                )
            else:
                messagebox.showinfo("Popular Items", "No data available.")

        except Exception as e:
            messagebox.showerror("Database Error", f"An error occurred: {e}")
        


    def voice_order(self):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            messagebox.showinfo("Voice Order", "Speak your order after the beep.")
            try:
                audio = recognizer.listen(source, timeout=5)
                order = recognizer.recognize_google(audio, language="ko-KR")
                self.process_voice_order(order)
            except sr.UnknownValueError:
                messagebox.showerror("Error", "Could not understand the audio.")
            except sr.RequestError:
                messagebox.showerror("Error", "Speech recognition service is not available.")
                
    # 음성인식 주문하기
    def process_voice_order(self, order):
        order = order.lower()
        if "blueberry" in order and "tropical" in order:
            self.orders.append(("Blueberry", "Tropical"))
        elif "strawberry" in order and "chocoring" in order:
            self.orders.append(("Strawberry", "Chocoring"))
        else:
            messagebox.showerror("Error", "Unrecognized order. Please try again.")

        if self.orders:
            self.update_current_order()

    def send_to_robot(self, mode, flavor=None, topping=None):
        # 아이스크림 모드와 쓰레기 버리기 모드 구분
        if mode == "ice_cream":
            if flavor is None or topping is None:
                messagebox.showerror("Error", "Flavor and topping must be provided for ice cream mode.")
                return

            
            topping_mapping = {
                "Tropical": "A",
                "Chocoring": "B",
                "Cereal": "C"
            }

            robot_topping = topping_mapping.get(topping, "Unknown")

            if robot_topping == "Unknown":
                messagebox.showerror("Error", "Unrecognized topping for robot communication.")
                return

            print(f"로봇에 전송 (아이스크림 모드): 맛={flavor}, 토핑={robot_topping}")

            """
            # 아이스크림 제조를 위한 실제 로봇 제어 코드      
            try:
                arm = XArmAPI('192.168.1.184', baud_checkset=False)
                robot_main = RobotMain(arm, robot_topping)
                robot_main.run()
            except Exception as e:
                messagebox.showerror("Error", f"Robot execution failed: {str(e)}")
                return  
            """

        elif mode == "trash_disposal":
            print("로봇에 전송 (쓰레기 버리기 모드): 쓰레기 버리기 명령")

            
            # 쓰레기 버리기를 위한 실제 로봇 제어 코드 
            try:
                arm = XArmAPI('192.168.1.184', baud_checkset=False)
                robot_main = RobotMain(arm,"C")
                robot_main.Trash_Throw()

            except Exception as e:
                messagebox.showerror("Error", f"Robot execution failed: {str(e)}")
                return  

                

        else:
            messagebox.showerror("Error", "Invalid mode selected.")
            return


    def update_current_order(self):
        if self.orders:
            flavor, topping = self.orders[0]
            self.current_order_text.config(text=f"맛: {flavor}, 토핑: {topping}")



# Initialize the main window
root = tk.Tk()
app = IceCreamOrderApp(root)
root.mainloop()
