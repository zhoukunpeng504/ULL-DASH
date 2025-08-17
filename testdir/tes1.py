# coding:utf-8
# write by zkp
import sys

with open("all_mp4_box.txt", "r") as f:
    content = f.readlines()


print([j for j in [i.strip() for i in content[::3]] if len(j) == 4])
