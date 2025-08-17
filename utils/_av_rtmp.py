# coding:utf-8
__author__ = "zkp"
# create by zkp on 2022/8/4
# import os,sys
# _ = os.path.abspath(os.path.join(os.path.dirname(__file__)))
# sys.path.append(_)


def av_recv_function(stream_index, rtmp_port, rtmp_path, sub_scribe_key,
                     redis_url,
                     process_name, parent_pid):
    import time, redis, os, datetime, psutil, fractions
    def print_to_logger(*args):
        "日志函数"
        file_name = os.path.join("/data/http_rtmp_streamer",
                                 f"rtmp_recv-{datetime.datetime.now().strftime('%Y%m%d')}.log")
        now = datetime.datetime.now().isoformat(sep=' ', timespec='milliseconds')
        try:
            msg = " ".join([str(i) for i in args])
            with open(file_name, "a+") as f:
                f.write(f"[{now}: INFO]:{msg}\n")
        except:
            pass

    redis_conn = redis.Redis.from_url(redis_url)

    # 开始正常业务处理流程
    import av
    av.logging.set_level(av.logging.CRITICAL)
    print("start av_recv_function", time.time())
    import time
    import sys
    import traceback, random, string
    import psutil
    import pickle, json
    import os
    import struct
    import bitstring
    # from av import bitstream


    def parse_avcc_hex(data: bytes):
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
            sps_length = struct.unpack(">H", data[offset:offset + 2])[0]
            offset += 2
            sps = data[offset:offset + sps_length]
            sps_list.append(sps)
            offset += sps_length

        pps_count = data[offset]
        offset += 1
        for _ in range(pps_count):
            pps_length = struct.unpack(">H", data[offset:offset + 2])[0]
            offset += 2
            pps = data[offset:offset + pps_length]
            pps_list.append(pps)
            offset += pps_length

        return sps_list[0].hex(), pps_list[0].hex()

    trans_gop_size = os.environ.get('GOPSIZE', None) or os.environ.get('GOP_SIZE', None) or '50'
    trans_gop_size = int(trans_gop_size)
    # import ctypes
    current_dir = os.path.abspath(os.path.dirname(__file__))
    sys.path.append(current_dir)
    try:
        import md5
    except:
        from . import md5
    # 删除老的标识文件
    import setproctitle
    setproctitle.setproctitle(process_name)
    os.system("mkdir -p /data/http_rtmp_streamer")
    output_kw_params = {"video": {},
                        "audio": {},
                        'nv_hw': None}  # 输出flv核心参数

    #with open(os.path.abspath(os.path.join(current_dir, "..", "config.json")), "r") as f:
    kwargs = {
        "format": "flv",
        "container_options": {
            "listen": "1",
            "fflags": "nobuffer"
        }
    }
    print_to_logger("kwargs", kwargs)
    all_codecs = av.codecs_available
    nv_hw = False
    output_kw_params['nv_hw'] = nv_hw
    print_to_logger("nvidia hw codec status", nv_hw)
    rtmp_url = f'rtmp://0.0.0.0:{rtmp_port}{rtmp_path}'

    def get_fraction_obj(time_base:str):
        _a,_b = time_base.split('/')
        _a,_b = int(_a),int(_b)
        return fractions.Fraction(_a,_b)

    while True:
        output_kw_params['video'] = {}
        output_kw_params['audio'] = {}
        try:
            print_to_logger("av open", rtmp_url)
            input_av = av.open(rtmp_url, 'r',
                            #metadata_errors='ignore',
                            # format=format,
                            timeout=None,
                            **kwargs
                            )
            print_to_logger("av open ...")
            print_to_logger("input_av flags", input_av.flags)
            video = input_av.streams.video[0]
            # 获取pps 和 sps数据 写入到redis
            video_extradata = video.codec_context.extradata
            video_sps, video_pps = parse_avcc_hex(video_extradata)
            redis_conn.set(f"chan_{stream_index}_pps",
                           bitstring.BitArray(hex=video_pps).bytes)
            redis_conn.set(f"chan_{stream_index}_sps",
                           bitstring.BitArray(hex=video_sps).bytes)
            # ######## end ###############

            #mp4toannexb_filter = bitstream.BitStreamFilterContext("h264_mp4toannexb",
            #                                            in_stream=video)
            code_name = video.codec_context.name
            print_to_logger("video code name is", code_name, video.codec_context.pix_fmt,
                            video.codec_context.profile)
            print_to_logger("#######")
            print_to_logger("video sps and pps", video_sps, video_pps)
            # _ =
            # need_encode = False
            # h264_codec = None
            def get_profile(codec_context):
                if not codec_context.profile:
                    if '444p' not in codec_context.pix_fmt:
                        return 'high'
                    else:
                        return 'high444p'
                return 'high'

            output_kw_params['video']['codec'] = 'h264'
            output_kw_params['video']['width'] = video.width
            output_kw_params['video']['height'] = video.height
            output_kw_params['video']['pix_fmt'] = video.codec_context.pix_fmt
            output_kw_params['video']['time_base'] = f"{video.time_base.numerator}/{video.time_base.denominator}"
            if video.base_rate.numerator <= 100:
                output_kw_params['video']['rate'] = f"{video.base_rate.numerator}/{video.base_rate.denominator}"
            else:
                output_kw_params['video']['rate'] = f"25/1"
            output_kw_params['video']['color_primaries'] = video.codec_context.color_primaries
            output_kw_params['video']['color_range'] = video.codec_context.color_range
            output_kw_params['video']['color_trc'] = video.codec_context.color_trc
            output_kw_params['video']['colorspace'] = video.codec_context.colorspace
            output_kw_params['video']['profile'] = get_profile(video.codec_context)
            video_params = output_kw_params['video']
            h264_codec_w = av.CodecContext.create('h264', "w")
            h264_codec_w.pix_fmt = video.codec_context.pix_fmt
            h264_codec_w.width = video.width
            h264_codec_w.height = video.height
            h264_codec_w.time_base = get_fraction_obj(output_kw_params['video']['time_base'])  # video_params['time_base']
            h264_codec_w.options = {"level": '42',
                                    #'Profile': 'High',
                                    'tune': 'zerolatency',
                                    'preset': 'ultrafast',
                                    'crf': '10',
                                    'threads': '10',
                                    # 'color_primaries': str(color_primaries),
                                    # 'color_range': str(color_range),
                                    # 'color_trc': str(color_trc),
                                    # 'colorspace': str(colorspace),
                                    'profile': output_kw_params['video']['profile'],  # '3', # str(profile).lower(),
                                    'rc': "vbr",
                                    'x264-params': 'keyint=1:min-keyint=1'
                                    # 'rgb_mode': "1"
                                    }
            # h264_codec_w.gop_size = 25  # 设置gop 为25
            # h264_codec_w.gop_size = video_params['gop_size']
            color_primaries = video_params['color_primaries']
            color_range = video_params['color_range']
            color_trc = video_params['color_trc']
            colorspace = video_params['colorspace']
            h264_codec_w.color_primaries = int(color_primaries)
            # h264_codec_w.gop_size = 25  # 设置gop 为25
            h264_codec_w.bit_rate = 8192000
            h264_codec_w.color_range = int(color_range)
            h264_codec_w.color_trc = int(color_trc)
            h264_codec_w.colorspace = int(colorspace)
            h264_codec_w.rate = get_fraction_obj(video_params['rate'])
            h264_codec_w.framerate = get_fraction_obj(video_params['rate'])
            print_to_logger("### h264_codec_w is ", h264_codec_w)



            print_to_logger("output_kw_params", output_kw_params)

            redis_conn.set(f"{sub_scribe_key}-params", json.dumps(output_kw_params))
            redis_conn.delete(f'{sub_scribe_key}-cache')
            v_counter = 0
            a_counter = 0
            late_iframe_counter = 0
            find_iframe_v = False
            for _p in input_av.demux():
                packet_time = time.time()
                # 应对某些视频流第一个packet不是关键帧
                if find_iframe_v == False:
                    if _p.is_keyframe:
                        find_iframe_v = True
                    else:
                        continue
                if _p.pts == None and _p.dts == None:
                    _p.pts = 0
                    _p.dts = 0
                else:
                    _p.pts = _p.dts = (_p.dts or _p.pts) + 3600
                # ########
                # _p.dts = _p.pts
                if _p.stream.type == 'video':
                    # 视频帧
                    target_packet = None
                    target_frame = None
                    #if code_name not in ('h265', 'hevc'):
                        # 无需转码
                    frames = _p.decode()
                    if frames:
                        target_packet = _p
                        target_frame = frames[0]

                    if target_packet and target_frame:
                        v_counter += 1
                        if target_packet.is_keyframe:
                            late_iframe_counter = v_counter
                        frame_type = target_frame.pict_type
                        w_packets = h264_codec_w.encode(target_frame)
                        w_i_packet = w_packets[0]
                        print_to_logger("target_packet_v", target_packet, frame_type,
                                        target_packet.is_keyframe, v_counter,
                                        late_iframe_counter)

                        print_to_logger("w_i_packet_v", w_i_packet,
                                        w_i_packet.is_keyframe)

                        packet_bytes = bytes(target_packet)
                        # with open("/tmp/h264-packet.h264", "wb+") as packet_file:
                        #     packet_file.write(packet_bytes)

                        send_data = pickle.dumps(
                                {'packet_bytes': packet_bytes,
                                 'packet_counter': v_counter,
                                 "time": packet_time,
                                 "dts": target_packet.dts,
                                 'pts': target_packet.pts,
                                 "is_key": target_packet.is_keyframe,
                                 "late_iframe_counter": late_iframe_counter,
                                 "packet_type": "video",
                                 'i_packet_bytes': bytes(w_i_packet),
                                 #'frame_ndarray': target_frame.to_ndarray(),
                                 #'frame_format': target_frame.format.name,
                                 'frame_pts': target_packet.pts
                                 }
                            )
                        # redis_conn.hset(f'{sub_scribe_key}-cache',
                        #                 str(v_counter % 500),
                        #                 pickle.dumps({'frame_ndarray': target_frame.to_ndarray(),
                        #                               'frame_format': target_frame.format.name,
                        #                               'frame_pts': target_packet.pts})
                        #                 )

                        try:
                            redis_conn.publish(sub_scribe_key, send_data)
                        except (Exception, BaseException) as e:
                            print_to_logger(f"pub to redis {sub_scribe_key} except:", str(e))
                            print_to_logger(traceback.format_exc())



        except (Exception, BaseException, av.error.FFmpegError) as e:
            print_to_logger("#######", str(e))
            print_to_logger(traceback.format_exc())
        finally:
            try:
                input_av.close()
            except:
                pass
            try:
                h264_codec_w.flush_buffers()
            except:
                pass
            try:
                h264_codec_w.close()
            except:
                pass
        try:
            redis_conn.delete(f"{sub_scribe_key}-params")
            redis_conn.delete(f'{sub_scribe_key}-cache')
            redis_conn.publish(sub_scribe_key, pickle.dumps(
                {
                 'packet_type': "close"
                 }
            ))
            print_to_logger("send redis close msg!!")
        except:
            pass
