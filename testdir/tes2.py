# coding:utf-8
# write by zkp
import bitstring
import os,sys
import struct


with open("avc1_41437074.m4s", "rb") as f:
    data_bytes = f.read()

class Box(object):
    def __init__(self, name, data:bytes):
        self.name = name
        self.data = data

    @property
    def length(self):
        return 8 + len(self.data)

    def __repr__(self):
        return (f"<Box-{self.name}-size-{self.length}>")

    def __str__(self):
        return self.__repr__()


buff = []
while 1:
    if not data_bytes:
        break
    _len = bitstring.BitArray(data_bytes[:4]).uint
    buff.append(Box( data_bytes[4:8], data_bytes[8:]))
    data_bytes = data_bytes[_len:]
#print(buff)

class NALU(object):
    def __init__(self, nalu_type, data):
        self.type = nalu_type
        self.data = data

    def __repr__(self):
        return f"NALU(type={self.type}, size={len(self.data)})"

    def __str__(self):
        return self.__repr__()

    def print_bit_view(self):
        print(bitstring.BitArray(self.data))


def parse_mdat_to_nalus(mdat_bytes, length_size=4):
    """
    将mdat中的H.264 AVCC格式数据解析为NALU对象列表
    :param mdat_bytes: bytes, mdat部分的原始二进制数据
    :param length_size: NALU长度字段字节数，一般是4字节（可为1、2、4）
    :return: list[NALU]
    """
    nalus = []
    offset = 0
    total_size = len(mdat_bytes)

    while offset < total_size:
        # 检查是否越界
        if offset + length_size > total_size:
            print(f"Warning: Incomplete NALU length at offset {offset}")
            break

        # 读取长度字段
        nalu_len = int.from_bytes(mdat_bytes[offset:offset + length_size], byteorder='big')
        offset += length_size

        if offset + nalu_len > total_size:
            print(f"Warning: Incomplete NALU data at offset {offset}")
            break

        # 读取NALU数据
        nalu_data = mdat_bytes[offset:offset + nalu_len]
        offset += nalu_len

        # 解析NALU类型（取第一个字节低5位）
        nalu_type = nalu_data[0] & 0x1F
        nalus.append(NALU(nalu_type, nalu_data))

    return nalus

mdat1 = buff[1]
mdat2 = buff[4]
mdat3 = buff[7]
mdat4 = buff[10]

nalus_1 = parse_mdat_to_nalus(mdat1.data)
nalus_2 = parse_mdat_to_nalus(mdat2.data)
nalus_3 = parse_mdat_to_nalus(mdat3.data)
nalus_4 = parse_mdat_to_nalus(mdat4.data)
print(nalus_1)
print(nalus_2)
print(nalus_3)
print(nalus_4)
print('##########')
for i in nalus_1:
    print(i,i.type)
    i.print_bit_view()








