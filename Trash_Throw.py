#!/usr/bin/env python3
# Software License Agreement (BSD License)
#
# Copyright (c) 2022, UFACTORY, Inc.
# All rights reserved.
#
# Author: Vinman <vinman.wen@ufactory.cc> <vinman.cub@gmail.com>

"""
# Notice
#   1. Changes to this file on Studio will not be preserved
#   2. The next conversion will overwrite the file with the same name
# 
# xArm-Python-SDK: https://github.com/xArm-Developer/xArm-Python-SDK
#   1. git clone git@github.com:xArm-Developer/xArm-Python-SDK.git
#   2. cd xArm-Python-SDK
#   3. python setup.py install
"""
import sys
import math
import time
import queue
import datetime
import random
import traceback
import threading
from xarm import version
from xarm.wrapper import XArmAPI


class RobotMain(object):
    """Robot Main Class"""
    def __init__(self, robot,topping,**kwargs):
        self.alive = True
        self._arm = robot
        self._tcp_speed = 100/2
        self._tcp_acc = 2000/2
        self._angle_speed = 20/2
        self._angle_acc = 500/2
        self.order_msg='A'
        #self.order_msg_topping=check
        self.order_msg_topping_pos=topping
        self._vars = {}
        self._funcs = {}
        self._robot_init()

        self.position_home = [179.2, -42.1, 7.4, 186.7, 41.5, -1.6]  # angle
        self.position_jig_A_grab = [-257.3, -138.3, 198, 68.3, 86.1, -47.0]  # linear
        self.position_jig_B_grab = [-152.3, -129.0, 198, 4.8, 89.0, -90.7]  # linear
        self.position_jig_C_grab = [-76.6, -144.6, 198, 5.7, 88.9, -50.1]  # linear
        self.position_sealing_check = [-136.8, 71.5, 307.6, 69.6, -73.9, -59]  # Linear
        self.position_capsule_place = [234.9, 135.9, 465.9, 133.6, 87.2, -142.1]  # Linear
        self.position_before_capsule_place = self.position_capsule_place.copy()
        self.position_before_capsule_place[2] += 25
        self.position_cup_grab = [214.0, -100.2, 145.0, -25.6, -88.5, 95.8]  # linear
        # topping before icecream
        self.position_topping_A = [-200.3, 162.8, 359.9, -31.7, 87.8, 96.1]  # Linear
        self.position_topping_B = [106.5, -39.7, 15.0, 158.7, 40.4, 16.9]  # Angle
        self.position_topping_C = [43.6, 137.9, 350.1, -92.8, 87.5, 5.3]  # Linear
        self.position_icecream_with_topping = [168.7, 175.6, 359.5, 43.9, 88.3, 83.3]  # Linear
        self.position_icecream_no_topping = [48.4, -13.8, 36.3, 193.6, 42.0, -9.2]  # angle
        # topping after icecream
        self.position_topping_A_later = [-197.7, 159.7, 305.4, 102.6, 89.3, -129.7]  # Linear
        self.position_topping_B_later = [-47.7, 159.7, 305.4, 102.6, 89.3, -129.7]  # Linear
        self.position_topping_C_later = [56.2, 142.7, 316.8, 162.2, 88.4, -92.0]  # Linear
        self.position_jig_A_serve = [-258.7, -136.4, 208.2, 43.4, 88.7, -72.2]  # Linear
        self.position_jig_B_serve = [-166.8, -126.5, 200.9, -45.2, 89.2, -133.6]  # Linear
        self.position_jig_C_serve = [-63.1, -138.2, 199.5, -45.5, 88.1, -112.1]  # Linear
        self.position_capsule_grab = [234.2, 129.8, 464.5, -153.7, 87.3, -68.7]  # Linear
    # Robot init
    def _robot_init(self):
        self._arm.clean_warn()
        self._arm.clean_error()
        self._arm.motion_enable(True)
        self._arm.set_mode(0)
        self._arm.set_state(0)
        time.sleep(1)
        self._arm.register_error_warn_changed_callback(self._error_warn_changed_callback)
        self._arm.register_state_changed_callback(self._state_changed_callback)
        if hasattr(self._arm, 'register_count_changed_callback'):
            self._arm.register_count_changed_callback(self._count_changed_callback)

    # Register error/warn changed callback
    def _error_warn_changed_callback(self, data):
        if data and data['error_code'] != 0:
            self.alive = False
            self.pprint('err={}, quit'.format(data['error_code']))
            self._arm.release_error_warn_changed_callback(self._error_warn_changed_callback)

    # Register state changed callback
    def _state_changed_callback(self, data):
        if data and data['state'] == 4:
            self.alive = False
            self.pprint('state=4, quit')
            self._arm.release_state_changed_callback(self._state_changed_callback)

    # Register count changed callback
    def _count_changed_callback(self, data):
        if self.is_alive:
            self.pprint('counter val: {}'.format(data['count']))

    def _check_code(self, code, label):
        if not self.is_alive or code != 0:
            self.alive = False
            ret1 = self._arm.get_state()
            ret2 = self._arm.get_err_warn_code()
            self.pprint('{}, code={}, connected={}, state={}, error={}, ret1={}. ret2={}'.format(label, code, self._arm.connected, self._arm.state, self._arm.error_code, ret1, ret2))
        return self.is_alive

    @staticmethod
    def pprint(*args, **kwargs):
        try:
            stack_tuple = traceback.extract_stack(limit=2)[0]
            print('[{}][{}] {}'.format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())), stack_tuple[1], ' '.join(map(str, args))))
        except:
            print(*args, **kwargs)

    @property
    def arm(self):
        return self._arm

    @property
    def VARS(self):
        return self._vars

    @property
    def FUNCS(self):
        return self._funcs

    @property
    def is_alive(self):
        if self.alive and self._arm.connected and self._arm.error_code == 0:
            if self._arm.state == 5:
                cnt = 0
                while self._arm.state == 5 and cnt < 5:
                    cnt += 1
                    time.sleep(0.1)
            return self._arm.state < 4
        else:
            return False
#------------------------motion------------------------
    def motion_home(self):

            code = self._arm.set_cgpio_analog(0, 0)
            if not self._check_code(code, 'set_cgpio_analog'):
                return
            code = self._arm.set_cgpio_analog(1, 0)
            if not self._check_code(code, 'set_cgpio_analog'):
                return

            # press_up
            code = self._arm.set_cgpio_digital(0, 0, delay_sec=0)
            if not self._check_code(code, 'set_cgpio_digital'):
                return

            # Joint Motion
            self._angle_speed = 80
            self._angle_acc = 200
            
            print('motion_home start')
            code = self._arm.set_servo_angle(angle=self.position_home, speed=self._angle_speed,
                                            mvacc=self._angle_acc, wait=True, radius=0.0)
            if not self._check_code(code, 'set_servo_angle'):
                return
            code = self._arm.stop_lite6_gripper()
            if not self._check_code(code, 'stop_lite6_gripper'):
                return
            print('motion_home finish')
    def motion_grab_capsule(self):

            code = self._arm.set_cgpio_analog(0, 5)
            if not self._check_code(code, 'set_cgpio_analog'):
                return
            code = self._arm.set_cgpio_analog(1, 5)
            if not self._check_code(code, 'set_cgpio_analog'):
                return

            # Joint Motion
            self._angle_speed = 100
            self._angle_acc = 100/2

            self._tcp_speed = 100
            self._tcp_acc = 1000/2

        
        
            code = self._arm.stop_lite6_gripper()
            if not self._check_code(code, 'stop_lite6_gripper'):
                return
            time.sleep(0.5)

            
            code = self._arm.set_servo_angle(angle=[166.1, 30.2, 25.3, 75.3, 93.9, -5.4], speed=self._angle_speed,
                                                mvacc=self._angle_acc, wait=True, radius=0.0)
            if not self._check_code(code, 'set_servo_angle'):
                return

            code = self._arm.open_lite6_gripper()
            if not self._check_code(code, 'open_lite6_gripper'):
                return
            time.sleep(1)

            
            
            code = self._arm.set_servo_angle(angle=[182.6, 27.8, 27.7, 55.7, 90.4, -6.4], speed=self._angle_speed,
                                            mvacc=self._angle_acc, wait=True, radius=0.0)
            if not self._check_code(code, 'set_servo_angle'):
                return
            # code = self._arm.set_position(*[-76.6, -144.6, 194.3, 5.7, 88.9, -50.1], speed=self._tcp_speed, mvacc=self._tcp_acc, radius=0.0, wait=True)
            # if not self._check_code(code, 'set_position'):
            #    return
            code = self._arm.set_position(*self.position_jig_C_grab, speed=self._tcp_speed,
                                        mvacc=self._tcp_acc, radius=0.0, wait=True)
            if not self._check_code(code, 'set_position'):
                return

            code = self._arm.close_lite6_gripper()
            if not self._check_code(code, 'close_lite6_gripper'):
                return

            time.sleep(1)
            
            code = self._arm.set_position(z=150, radius=0, speed=self._tcp_speed, mvacc=self._tcp_acc, relative=True,
                                        wait=False)
            if not self._check_code(code, 'set_position'):
                return

            code = self._arm.set_tool_position(*[0.0, 0.0, -90.0, 0.0, 0.0, 0.0], speed=self._tcp_speed,
                                            mvacc=self._tcp_acc, wait=True)
            if not self._check_code(code, 'set_position'):
                return
            
            self._angle_speed = 160
            self._angle_acc = 200

            code = self._arm.set_servo_angle(angle=[146.1, -10.7, 10.9, 102.7, 92.4, 24.9], speed=self._angle_speed,
                                            mvacc=self._angle_acc, wait=False, radius=20.0)
            if not self._check_code(code, 'set_servo_angle'):
                return
            code = self._arm.set_servo_angle(angle=[81.0, -10.8, 6.9, 103.6, 88.6, 9.6], speed=self._angle_speed,
                                         mvacc=self._angle_acc, wait=False, radius=40.0)
            if not self._check_code(code, 'set_servo_angle'):
                return
            code = self._arm.set_servo_angle(angle=[59.7,-10.8,6.9,103.6,88.6,180.4], speed=self._angle_speed,
                                            mvacc=self._angle_acc, wait=False, radius=20.0)
            if not self._check_code(code, 'set_servo_angle'):
                return
            code = self._arm.open_lite6_gripper()
            if not self._check_code(code, 'open_lite6_gripper'):
                return
            time.sleep(5)
            code = self._arm.set_servo_angle(angle=[81.0, -10.8, 6.9, 103.6, 88.6, 9.6], speed=self._angle_speed,
                                         mvacc=self._angle_acc, wait=False, radius=0.0)
            if not self._check_code(code, 'set_servo_angle'):
                return
            code = self._arm.set_servo_angle(angle=[179.2, -42.1, 7.4, 186.7, 41.5, -1.6], speed=20,
                                         mvacc=500, wait=True, radius=0.0)
            if not self._check_code(code, 'set_servo_angle'):
                return
            code = self._arm.stop_lite6_gripper()
            if not self._check_code(code, 'stop_lite6_gripper'):
                return
    def run(self):
        try:
            self.motion_grab_capsule()
            self.motion_home()
            #self.motion_trash_capsule()
            
            print('icecream finish')
            
        except Exception as e:
            self.pprint('MainException: {}'.format(e))
        self.alive = False
        self._arm.release_error_warn_changed_callback(self._error_warn_changed_callback)
        self._arm.release_state_changed_callback(self._state_changed_callback)
        if hasattr(self._arm, 'release_count_changed_callback'):
            self._arm.release_count_changed_callback(self._count_changed_callback)


if __name__ == '__main__':
    RobotMain.pprint('xArm-Python-SDK Version:{}'.format(version.__version__))
    arm = XArmAPI('192.168.1.184', baud_checkset=False)
    robot_main = RobotMain(arm,'C')
    robot_main.run()