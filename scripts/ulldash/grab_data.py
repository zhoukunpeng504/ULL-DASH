# coding:utf-8
# write by zkp
# 通过自动化点击网页播放
# 获取原始的播放延迟数据
import os
import sys
from PIL import ImageGrab
import subprocess
import multiprocessing as mp
import psutil
import time
import datetime
import random
import pyautogui


def grab_screen(save_path, width=1920, height=1080):
    img = ImageGrab.grab(bbox=(0, 0, width, height))
    img.save(save_path, format='PNG')


def click(pos_x:int, pos_y:int):
    # 延迟2秒
    time.sleep(0.4)
    # duration 鼠标移动时间
    # pyautogui.moveTo(x, y, duration=num_seconds)
    # 将鼠标移动到指定位置
    pyautogui.moveTo(pos_x, pos_y)
    time.sleep(0.2)
    # 点击
    pyautogui.click()


def re_play():
    # stop play
    click(1465,210)
    time.sleep(0.2)
    click(1465, 210)
    time.sleep(0.2)
    click(1526, 201)
    time.sleep(4)
    #click(1662,206)
    #time.sleep(13+gop_size/2)





if __name__ == '__main__':
    gop_size = int(sys.argv[-1].strip())
    pix_name = 'ulldash'
    try:
        os.mkdir(f"latency_data_{pix_name}")
    except:
        pass
    for trys in range(1, 190):
        # if trys % 2 == 1:
        re_play()
        print("replay ..", trys)
        try:
            os.mkdir(f'latency_data_{pix_name}/gop_{gop_size}')
        except:
            pass
        #save_path = f'latency_data_{pix_name}/gop_{gop_size}/{name}/times-{trys}-{dur}_s.jpg'
        save_path = f'latency_data_{pix_name}/gop_{gop_size}/{trys}_s.png'
        print("grab image", save_path)
        grab_screen(save_path)
        time.sleep(1)




