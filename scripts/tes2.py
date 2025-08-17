# coding:utf-8
# write by zkp
import av
import struct

#url = "rtmp://liteavapp.qcloud.com/live/liteavdemoplayerstreamid"  # RTMP 流地址
url = 'rtmp://ns8.indexforce.com/home/mystream'
container = av.open(url)

video_stream = next(s for s in container.streams if s.type == "video")
extradata = video_stream.codec_context.extradata

print("Extradata (hex):", extradata.hex())

def parse_avcc_hex(data:bytes):
    """
    解析 AVCDecoderConfigurationRecord 获取 SPS 和 PPS （hex格式）
    格式参考 ISO/IEC 14496-15
    """
    sps_list = []
    pps_list = []

    if len(data) < 7:
        return sps_list, pps_list

    # 跳过前 5 字节：configurationVersion, AVCProfileIndication, profile_compatibility,
    # AVCLevelIndication, lengthSizeMinusOne
    sps_count = data[5] & 0x1F
    offset = 6
    for _ in range(sps_count):
        sps_length = struct.unpack(">H", data[offset:offset+2])[0]
        offset += 2
        sps = data[offset:offset+sps_length]
        sps_list.append(sps)
        offset += sps_length

    pps_count = data[offset]
    offset += 1
    for _ in range(pps_count):
        pps_length = struct.unpack(">H", data[offset:offset+2])[0]
        offset += 2
        pps = data[offset:offset+pps_length]
        pps_list.append(pps)
        offset += pps_length

    return sps_list[0].hex(), pps_list[0].hex()

sps_list, pps_list = parse_avcc_hex(extradata)
print(sps_list, pps_list)
# raise
# for i, sps in enumerate(sps_list):
#     print(f"SPS[{i}]: {sps.hex()}")
#
# for i, pps in enumerate(pps_list):
#     print(f"PPS[{i}]: {pps.hex()}")
