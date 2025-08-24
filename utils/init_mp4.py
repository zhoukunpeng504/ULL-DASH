# coding:utf-8
# write by zkp
import bitstring
import random
import typing
import copy
from bitstring import BitArray
import os, sys

all_mp4_boxes = ['2dqr', '2dss', 'ainf', 'assp', 'auxi', 'avcn', 'bidx', 'bloc', 'bmdm', 'bpcc', 'brob', 'buff',
                 'bxml', 'ccid', 'ccst', 'cdef', 'cinf', 'clip', 'cmap', 'co64', 'coif', 'coin', 'colr', 'covi',
                 'crgn', 'crhd', 'csgp', 'cslg', 'cstb', 'ctab', 'ctts', 'cvru', 'dihd', 'dinf', 'dint', 'dmon',
                 'dref', 'dsgd', 'dstg', 'edts', 'elst', 'emsg', 'evti', 'etyp', 'Exif', 'fdel', 'feci', 'fecr',
                 'fidx', 'fiin', 'fire', 'fovd', 'fovi', 'fpar', 'free', 'frma', 'frpa', 'ftyp', 'fvsi', 'gitn',
                 'grpi', 'grpl', 'hdlr', 'hmhd', 'hpix', 'icnu', 'ID32', 'idat', 'ihdr', 'iinf', 'iloc', 'imap',
                 'imda', 'imif', 'infe', 'infu', 'iods', 'ipco', 'iphd', 'ipma', 'ipmc', 'ipro', 'iprp', 'iref',
                 'j2kH', 'j2kP', 'jbrd', 'jp2c', 'jp2h', 'jp2i', 'jumb', 'jxll', 'jxlc', 'jxli', 'jxlp', 'jpvi',
                 'jpvs', 'jptp', 'jxpl', 'kmat', 'leva', 'load', 'loop', 'lrcu', 'm7hd', 'matt', 'md5i', 'mdat',
                 'mdhd', 'mdia', 'mdri', 'meco', 'mehd', 'meof', 'mere', 'mesh', 'meta', 'mfhd', 'mfra', 'mfro',
                 'minf', 'mjhd', 'mmvi', 'moof', 'moov', 'movd', 'mstv', 'mvcg', 'mvci', '3dpr', 'mvex', 'mvhd',
                 'mvra', 'nmhd', 'ochd', 'odaf', 'odda', 'odhd', 'odhe', 'odrb', 'odrm', 'odtt', 'ohdr', 'otcf',
                 'otyp', 'ovly', 'padb', 'paen', 'pclr', 'pdat', 'pdin', 'pfhd', 'pfil', 'pitm', 'ploc', 'pnot',
                 'povd', 'prfr', 'prft', 'pseg', 'pshd', 'pssh', 'ptle', 'resc', 'resd', 'rinf', 'rotn', 'rosc',
                 'rvif', 'rwpk', 'saio', 'saiz', 'sbgp', 'schi', 'schm', 'sdep', 'sdhd', 'sdtp', 'sdvp', 'segr',
                 'seii', 'senc', 'sgpd', 'sidx', 'sinf', 'skip', 'smhd', 'sprg', 'srmb', 'srmc', 'srpp', 'srqr',
                 'ssix', 'sstl', 'stbl', 'stco', 'stdp', 'sthd', 'stmg', 'strd', 'stri', 'stsc', 'stsd', 'stsg',
                 'stsh', 'stss', 'stsz', 'stti', 'stts', 'styp', 'stz2', 'subs', 'suep', 'sumi', 'surl', 'swtc',
                 'tenc', 'tfad', 'tfdt', 'tfhd', 'tfma', 'tfra', 'tibr', 'tiri', 'tkhd', 'traf', 'trak', 'tref',
                 'trep', 'trex', 'trgr', 'trik', 'trun', 'tstb', 'ttyp', 'tyco', 'udta', 'uinf', 'UITS', 'ulst',
                 'uuid', 'v3sc', 'vmhd', 'vpbb', 'vssn', 'vunt', 'vvhd', 'vwdi', 'wmpi', '!mof', '!mov', '!six',
                 '!ssx', 'iroi', 'ldep', 'rrgn', 'svdr', 'svip', 'svpr', 'tran', 'vipr', 'stvi', 'spki', 'aedb',
                 'aelm', 'aepp', 'aepr', 'aesb', 'aesd', 'ardi', 'labl', 'elng', 'rsot', 'ssrt']


class Mp4Box(object):
    def __init__(self, box_full_bytes:bytes):
        assert len(box_full_bytes) == bitstring.BitArray(box_full_bytes[:4]).uint
        # self.box_len:int = len(box_full_bytes)
        self.box_type:str = box_full_bytes[4:8].decode('ascii',errors='ignore')
        assert self.box_type in all_mp4_boxes
        self._init_box_data:bytes = box_full_bytes[8:]

        ###########################
        self._children_boxes = None
        self.parent = None

    @property
    def all_children(self):
        if not self._children_boxes:
            self._children_boxes = self._parse_children()
        return self._children_boxes

    @property
    def box_len(self):
        if not self.all_children:
            return len(self._init_box_data) + 8
        else:
            return sum([i.box_len for i in self.all_children]) + 8

    def __str__(self):
        return f'Mp4Box-{self.box_type}-{self.box_len}Bytes-Addr:{id(self)}'

    def __repr__(self):
        return f'Mp4Box-{self.box_type}-{self.box_len}Bytes-Addr:{id(self)}'

    def _parse_children(self):
        _ = self._init_box_data
        childs = []
        if len(_) <= 8:
            return []
        else:
            if _[4:8].decode(errors='ignore') not in all_mp4_boxes:
                return []
            else:
                while _:
                    _len = bitstring.BitArray(bytes=_[:4]).uint
                    child = Mp4Box(_[:_len])
                    child.parent = self
                    childs.append(child)
                    _ = _[_len:]
                return childs

    def update_data(self, box_data:bytes):
        self._init_box_data = box_data
        # self.box_len = len(box_data) + 8

    def to_bytes(self)->bytes:
        '把当前mp4 box转化为bytes'
        if not self.all_children:
            return (bitstring.BitArray(uint=self.box_len, length=32).tobytes()
                    + self.box_type.encode() + self._init_box_data)
        else:
            content = b''
            for child in self.all_children:
                content += child.to_bytes()
            return (bitstring.BitArray(uint=self.box_len, length=32).tobytes() +
                    self.box_type.encode() + content)

    def __bytes__(self):
        return self.to_bytes()


    def find_child(self, name:str, recursion=True):
        if not self.all_children:
            return
        if not recursion:
            for i in self.all_children:
                if i.box_type == name:
                    return i
        else:
            # if self.children_boxes
            loop_buff = self.all_children
            while len(loop_buff):
                _ = loop_buff[0]
                loop_buff = loop_buff[1:]
                if _.box_type == name:
                    return _
                else:
                    if _.all_children:
                        loop_buff = loop_buff + _.all_children




class AvcMp4(object):

    def __init__(self, timescale=10000000):
        self.timescale = timescale
        current_dir = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(current_dir,
                               "avc1_1280x720_25_1_init.mp4"), "rb") as f:
            self.template_mp4_bytes = f.read()
        self.template_ftyp = self.template_mp4_bytes[:28]
        self.template_moov_obj = Mp4Box(self.template_mp4_bytes[28:])

    def get_init_mp4(self,width:int, height:int,
                     profile:str, level:typing.Union[int, float],#int|float,
                     pps:bytes, sps:bytes):

        profile = profile.upper()
        profile_config = {'BASELINE':66, 'MAIN':77,
                           'EXTENDED':88, 'HIGH':100,
                           'HIGH10':110, 'HIGH422':122, 'HIGH444':144}
        assert profile in profile_config
        assert level in (1, 1.1, 1.2, 1.3,
                         2, 2.1, 2.2,
                         3, 3.1, 3.2,
                         4, 4.1, 4.2,
                         5, 5.1, 5.2)
        profile_int = profile_config[profile]
        trak = self.template_moov_obj.find_child("trak")
        tkhd = trak.all_children[0]
        tkhd_data = bitstring.BitArray(bytes=tkhd.to_bytes()[8:])
        width_bit_array = bitstring.BitArray(uint=width, length=32)
        height_bit_array = bitstring.BitArray(uint=height, length=32)
        tkhd_data[-48:-16] = height_bit_array
        tkhd_data[-80:-48] = width_bit_array
        tkhd.update_data(tkhd_data.tobytes())
        # print(trak)
        stsd_template_data = f'''00000000 00000001
        {bitstring.BitArray(uint=0x000000a4+(len(pps)+len(sps)-43), length=32).hex} 61766331 
        00000000 00000001
        00000000 00000000 00000000 00000000
        {bitstring.BitArray(uint=width,length=16).hex}{bitstring.BitArray(uint=height,length=16).hex} 00480000 00480000 
        00000000 00010468 32363400 00000000 00000000
        00000000 00000000 00000000 00000000
        00000018 ffff
        0000{bitstring.BitArray(uint=0x003e+(len(pps)+len(sps)-43), length=16).hex}6176 634301
        {bitstring.BitArray(uint=profile_int,length=8).hex}
        00{bitstring.BitArray(uint=int(level*10),length=8).hex}ffe1 
        {bitstring.BitArray(uint=len(sps),length=16).hex}{bitstring.BitArray(bytes=sps,length=len(sps)*8).hex}
        01{bitstring.BitArray(uint=len(pps),length=16).hex}{bitstring.BitArray(bytes=pps,length=len(pps)*8).hex} 
        00000010 70617370 00000001 00000001
        '''
        # 最后1行是 pasp 数据
        # 倒数第2行是 pps数据
        # 倒数第3行是 sps数据
        # 倒数第4行是 level数据
        # 倒数第5行是 profile数据
        # print(avc1)
        stsd_template_data = stsd_template_data.replace(" ","").replace("\n","").\
            replace("\r","").replace("\t","")
        stsd_data = bitstring.BitArray(hex=stsd_template_data)
        self.template_moov_obj.find_child("stsd").update_data(stsd_data.tobytes())
        # print(trak.children_boxes)
        return self.template_ftyp + self.template_moov_obj.to_bytes()


    def get_moof_mdat_free_data(self,
                                sequence_num:int,
                                decode_time:int,
                                mdat_data:bytes
                                ):
        '''
        :param sequence_num: 序列号
        :param decode_time: 解码时间,可以用dts 理解
        :param mdat_data: 视频帧真实数据
        :return:
        '''
        # moof-header
        #   mfhd-header  mfhd-data(后四位是sequence_num)
        #   traf
        #    - tfhd-header  data
        #    - tfdt-header  data
        #    - trun-header  data
        moof_hex = f'''000000686d6f6f66
                        000000106d666864  00000000{BitArray(uint=sequence_num,length=32).hex}
                        0000005074726166
                         0000001074666864  0002000000000101  
                         0000001474666474  01000000{BitArray(uint=decode_time,length=64).hex} 
                         000000247472756e00000b05  00000001000000700200000000061a80  {BitArray(uint=len(mdat_data),length=32).hex}000c3500'''
        moof_hex = moof_hex.replace(" ","").replace("\t","").\
            replace("\r","").replace("\n","")
        moof_bytes = bitstring.BitArray(hex=moof_hex).bytes
        return moof_bytes + self.get_mdat_data(mdat_data) + self.get_free_data()


    def get_mdat_data(self,data:bytes):
        mdat_ = f"{bitstring.BitArray(uint=len(data) + 8,length=32).hex}6d646174"
        return bitstring.BitArray(hex=mdat_).bytes + data

    def get_free_data(self):
        return bitstring.BitArray(hex="0000000866726565").tobytes()


if __name__ == '__main__':
    obj = AvcMp4()
    _1920_data = obj.get_init_mp4(1920,1080,
                                  'main', 4.1,
                                  b'aabbccddeeff',
                                  b"abababab")
    # with open("abka_init6.mp4", "wb") as f:
    #     f.write(_1920_data)
    # print(obj.template_moov_obj.all_children)
    with open("aaabbbccc.m4s", "wb") as f:
        for i in range(10):
            f.write(obj.get_moof_mdat_free_data(i, i, b"abcabcabcabc"))