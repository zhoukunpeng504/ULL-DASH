# coding:utf-8
# write by zkp
import av
import json
import os
import fractions
from PIL import Image
from av.packet import Packet
import io

input_ = av.open("./gop-video/gop-10.ts", "r")



def get_profile(codec_context):
    if not codec_context.profile:
        if '444p' not in codec_context.pix_fmt:
            return 'high'
        else:
            return 'high444p'
    return 'high'

def get_fraction_obj(time_base: str):
    _a, _b = time_base.split('/')
    _a, _b = int(_a), int(_b)
    return fractions.Fraction(_a, _b)

av_input_file = './gop-video/gop-10.ts'
input_av = av.open(av_input_file, "r")
video = input_av.streams.video[0]
psnr_data = []
h264_codec_r = av.CodecContext.create('h264', "r")
h264_codec_r.options = {
    'tune': 'zerolatency',
    'preset': 'ultrafast'
}
_io = io.BytesIO()
_io.name = 'out111.mpd'
av_out = av.open(_io, "w")
out_stream = av_out.add_stream(codec_name='h264', rate=30)
out_stream.codec_context.options = {
    'tune': 'zerolatency',
    'preset': 'ultrafast'
}
h264_codec_w = av.CodecContext.create('h264', "w")
h264_codec_w.pix_fmt = video.codec_context.pix_fmt
h264_codec_w.width = video.width
h264_codec_w.height = video.height
# h264_codec_w.time_base = get_fraction_obj(video_params['time_base'])  # video_params['time_base']
print("profile", get_profile(video.codec_context))
# raise
h264_codec_w.options = {"level": '42',
                        # 'Profile': 'High',
                        'tune': 'zerolatency',
                        'preset': 'ultrafast',
                        'crf': '10',
                        'threads': '10',
                        # 'color_primaries': str(color_primaries),
                        # 'color_range': str(color_range),
                        # 'color_trc': str(color_trc),
                        # 'colorspace': str(colorspace),
                        'profile': get_profile(video.codec_context),  # '3', # str(profile).lower(),
                        'rc': "vbr",
                        #'keyint': '1',
                        #'min-keyint':'1',
                        'x264-params': 'keyint=1:min-keyint=1'
                        # 'rgb_mode': "1"
                        }
# h264_codec_w.gop_size = 25  # 设置gop 为25
# h264_codec_w.gop_size = video_params['gop_size']
color_primaries = video.codec_context.color_primaries
color_range = video.codec_context.color_range
color_trc = video.codec_context.color_trc
colorspace = video.codec_context.colorspace
h264_codec_w.color_primaries = int(color_primaries)
# h264_codec_w.gop_size = 25  # 设置gop 为25
# h264_codec_w.bit_rate = 1250000
h264_codec_w.color_range = int(color_range)
h264_codec_w.color_trc = int(color_trc)
h264_codec_w.colorspace = int(colorspace)
h264_codec_w.rate = get_fraction_obj(f"{video.base_rate.numerator}/{video.base_rate.denominator}")
h264_codec_w.framerate = get_fraction_obj(f"{video.base_rate.numerator}/{video.base_rate.denominator}")
# av_input = av.open(av_input_file)

def copy_packet(pack:Packet):
    _p = Packet(bytes(pack))
    _p.pts = pack.pts
    _p.dts = pack.dts
    _p.is_keyframe = pack.is_keyframe
    return _p

frame_index = 0
keyframe_index = 0
for packet in input_av.demux(video=0):
    frame = packet.decode()[0]
    frame_index += 1
    if frame.key_frame:
        keyframe_index += 1

    # if keyframe_index >=2:
    #    break
    #print(frame, frame.key_frame)
    img = frame.to_ndarray(format='rgb24')

    # 使用PIL转换并保存为BMP
    #pil_img = Image.fromarray(img)
    #pil_img.save(f"/tmp/raw.bmp")
    #cv2_img = cv2.imread(f"/tmp/raw.bmp")

    #if keyframe_index == 1 and not frame.key_frame:
    av_out.mux(packet)
    if frame_index >10:
        if frame_index >= 11:
            packets = h264_codec_w.encode(frame)
            new_packet = packets[0]
            new_packet.stream = out_stream
            new_packet.dts = packet.dts
            new_packet.pts = packet.pts
            print("new_packet", packet,new_packet, new_packet.is_keyframe)
            #av_out.mux(new_packet)
            # h264_codec_r.decode(copy_packet(new_packet))
            # else:
            #     print("packet", packet)
            #     packet.stream = out_stream
            #     av_out.mux(packet)
        # if frame_index >= 12:
        #     res = h264_codec_r.decode(copy_packet(packet))
        #     print(res)
        #     img = res[0].to_ndarray(format='rgb24')
        #     pil_img = Image.fromarray(img)
        #     pil_img.save(f"{frame_index}raw.bmp")
        # if frame_index >= 20:
        #     raise



# for i in input_.demux(video=0):
#     i.dts += 100
#     i.pts += 100
#     i.stream = out_stream
#     print(i, i.is_keyframe)
#     av_out.mux(i)
