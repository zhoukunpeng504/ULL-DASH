# coding:utf-8
# write by zkp
import flask
from gevent.monkey import patch_all;patch_all(thread=True, subprocess=False)
import threading
import gevent
from gevent.pool import Pool
import traceback
import psutil
from urllib import parse
import socket
import random
import os
import setproctitle
import hashlib, base64, struct, time
import requests
import datetime
import redis
from utils import process_task, _av_rtmp, request_utils, init_mp4
import re
from flask import Flask, stream_with_context
import mimetypes,hashlib,subprocess
import requests
import random,sys
import jinja2
from flask import Response
import flask_cors
import pickle, json


#a = datetime.datetime.strptime("2025-08-11T11:23:35.962000Z","%Y-%m-%dT%H:%M:%S.%fZ")
#b = datetime.datetime.strptime('2023-01-01T00:00:02.800Z', '%Y-%m-%dT%H:%M:%S.%fZ')
#c = (a.timestamp()-b.timestamp()-1.96) /2 +1
#print(c)

os.system("mkdir -p /data/ulldash_streamer")


def print_to_logger(*args):
    now = datetime.datetime.now().isoformat(sep=' ', timespec='milliseconds')
    try:
        msg = " ".join([str(i) for i in args ])
        print(f"[{now}: INFO]:{msg}")
        #sys.stdout.flush()
    except Exception as e:
        print("logger err!!", str(e))
        pass
    sys.stdout.flush()


def gen_session_id():
    return hashlib.md5((str(random.random()) + str(time.time())).encode()).hexdigest()[:32]

app = Flask(__name__)
flask_cors.CORS(app)

dict_info = {"0":("1280","720"),
                 "1":("1920","1080"),
                 "2":("2560","1440"),
                 "3":("3840","2160"),}
TIME_OFFSET_S = 2.5

avail_timestamp = 1672531200.95

GLOBAL_BUFF = {0:{}, 1:{}, 2:{}, 3:{}}



# 如： /ulldash/0/main.mpd   0 对应720p
@app.route("/ulldash/<int:stream_index>/main.mpd")
def mpd_index(stream_index:int):
    global dict_info
    request = flask.request
    redis_conn = redis.Redis.from_url(redis_url)

    current_v_info = redis_conn.get(f"chan_{stream_index}_current_v_info")
    current_goplen = redis_conn.get(f"chan_{stream_index}_current_goplen")
    # current_v_time  = redis_conn.get(f"chan_{stream_index}_current_v_time")
    print_to_logger("###### current_goplen", current_goplen)
    if not current_v_info or not current_goplen:
        return Response('404 no stream',
                        content_type="html/text")
    current_goplen = int(current_goplen)
    current_v_info = json.loads(current_v_info)
    current_v_counter = current_v_info["v_counter"]
    current_v_time = current_v_info["time"]
    current_is_key = current_v_info["is_key"]

    ### 对 current_v_counter 进行处理
    if not current_is_key:
        # if current_v_counter % current_goplen <=5:
        #    current_v_counter = (current_v_counter // current_goplen) * current_goplen + 1
        # 假设current_goplen为25
        # v_counter 为1时， v_counter无需处理 为 1
        # v_counter 为2时， v_counter经过处理后 为 1
        # v_counter 为3时， v_counter经过处理后 为 1
        # v_counter 为6时， v_counter经过处理后 为 6
        # v_counter 为7时， v_counter经过处理后 为 6
        # v_counter 为11时， v_counter经过处理后 为 11
        # v_counter 为12时， v_counter经过处理后 为 11
        # v_counter 为17时， v_counter经过处理后 为 16
        # v_counter 为21时， v_counter经过处理后 为 21
        # v_counter 为26时， v_counter无需处理，为26
        # v_counter 为27时， v_counter经过处理后，为26
        # v_counter 为29时， v_counter经过处理后，为26
        # v_counter 为30时， v_counter经过处理后，为26
        if 5 >= ((current_v_counter % current_goplen) % 10) >= 1 :
            current_v_counter = current_v_counter //10 * 10 + 1
        else:
            current_v_counter = current_v_counter // 10 * 10 + 6
        _data = redis_conn.get(f'{stream_index}-cache-counter{current_v_counter}')
        current_v_info = pickle.loads(_data)
        current_v_time = current_v_info["time"]
        current_is_key = current_v_info["is_key"] #

    with open("./template.mpd", "r") as f:
        template = jinja2.Template(f.read())
    width, height = dict_info[str(stream_index)]


    now = datetime.datetime.now().astimezone(datetime.timezone.utc)
    utc_value = now.strftime("%Y-%m-%dT%H:%M:%S.%fZ") # 2025-08-13T02:02:03.789000Z
    # publishTime = now.strftime("%Y-%m-%dT%H:%M:%SZ")  # 2025-08-13T02:02:03Z
    # publishTime = (datetime.datetime.fromtimestamp(now.timestamp()
    #                                               - current_v_counter*0.025
    #                                               )
    #                .astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    # (publishTime)

    segment_size = current_goplen        # gop_len * 25
    current_s_t = int((current_v_time - avail_timestamp) * 10000000)
    current_s_frames = (segment_size - current_v_counter % segment_size) + 1
    current_s_d = current_s_frames * 400000
    GLOBAL_BUFF[stream_index][current_s_t] = (current_v_counter, current_s_frames)

    for i in range(2000):
        GLOBAL_BUFF[stream_index][current_s_t + current_s_d + segment_size*i*400000] = \
            (current_v_counter + current_s_frames + segment_size*i,
             segment_size)

    redis_conn.close()
    response_content = template.render(width=width,
                                       height=height,
                                       stream_index=stream_index,
                                       #publishTime=publishTime,
                                       utc_value=utc_value,
                                       #gop_len=gop_len,
                                       current_goplen=current_goplen,
                                       current_s_t=current_s_t,
                                       current_s_d=current_s_d,
                                       # session_id=gen_session_id()
                                       )
    return Response(response_content, content_type="application/dash+xml")


@app.route("/dash/chan<int:stream_index>_init.mp4")
def chan_init(stream_index:int):
    # stream_index  通道编号。一共4个通道
    # gop_len  GOP长度。
    # 具体配置如上 dict_info中所示
    # profile 按照HIGH
    # level  按照4.2
    # pps 和 sps 从推流时的写入的内存参数中获取， 如果获取不到，则返回404
    # ####################################
    # conn = redis.Redis.from_url(redis_url)
    global dict_info
    assert str(stream_index) in dict_info
    width, height = dict_info[str(stream_index)]
    redis_conn = redis.Redis.from_url(redis_url)
    pps_data:bytes = redis_conn.get(f"chan_{stream_index}_pps")
    sps_data:bytes = redis_conn.get(f"chan_{stream_index}_sps")
    if not pps_data  or not sps_data:
        resp = Response('404', status=404, mimetype='video/mp4')
    else:
        mp4_obj = init_mp4.AvcMp4()
        mp4_bytes = mp4_obj.get_init_mp4(width, height,
                             'high',4.2,
                             pps_data,sps_data)
        resp = Response(mp4_bytes, status=200, mimetype='video/mp4')
    resp.headers['Cache-Control'] = 'no-cache'
    resp.headers['Server'] = 'flask'
    redis_conn.close()
    return resp


@app.route("/dash/chan<int:stream_index>-<int:time_d>.m4s")
def chan_m4s(stream_index:int, time_d:int):
    # 返回切片mp4文件
    # #############
    # 一个segment 返回一个gop长度的大小，既 gop_len * 帧率。
    # 这里帧率统一认为是25fps
    global GLOBAL_BUFF
    redis_conn = redis.Redis.from_url(redis_url)
    current_v_info = redis_conn.get(f"chan_{stream_index}_current_v_info")
    current_goplen = redis_conn.get(f"chan_{stream_index}_current_goplen")
    if not current_v_info:
        return Response('',
                        content_type="video/mp4")
    current_goplen = int(current_goplen)
    current_v_info = json.loads(current_v_info)
    current_v_counter = current_v_info["v_counter"]
    current_v_time = current_v_info["time"]
    # now = datetime.datetime.now()
    # total_frame_num = gop_len * 25
    # number_ = time_d
    print("time_d", time_d)
    assert time_d in GLOBAL_BUFF[stream_index]
    req_v_counter, req_frames = GLOBAL_BUFF[stream_index][time_d]

    # all_frame_num = gop_len * 25 - current_v_counter % (gop_len * 25)
    # t_now = (number_ - 1) * 10000000 * gop_len + TIME_OFFSET_S + \
    #     datetime.datetime.strptime('2023-01-01T00:00:01.950Z',
    #                                '%Y-%m-%dT%H:%M:%S.%fZ').timestamp()
    # print("#####t_now", datetime.datetime.fromtimestamp(t_now), now)
    # chan_subscribe_key = hashlib.md5(f'/live/chan{stream_index}'\
    #                                  .encode('utf-8')).hexdigest()[:10]
    init_obj = init_mp4.AvcMp4()


    @stream_with_context
    def return_fun():
        for i in range(req_frames):
            v_counter = req_v_counter + i
            v_counter_time = time_d + i * 400000
            data = b''
            for j in range(30):
                # 重试30次
                data = redis_conn.get(f'{stream_index}-cache-counter{v_counter}')
                if not data:
                    gevent.sleep(0.1)
                else:
                    break
            if not data:
                return Response(b'404', status=404, mimetype='video/mp4')
            else:
                pass
            data_obj = pickle.loads(data)
            data_frame_i = data_obj['i_packet_bytes']
            data_frame_raw = data_obj['packet_bytes']
            # # 采用所有i帧
            if req_frames != current_goplen:
                _data = init_obj.get_moof_mdat_free_data(v_counter, v_counter_time,
                                                             data_frame_i)
            else:
                _data = init_obj.get_moof_mdat_free_data(v_counter, v_counter_time,
                                                         data_frame_raw)

            # 只采用第一个I帧
            # if i == 0:
            #     if req_frames == current_goplen:
            #         # 直接返回原始数据
            #         _data = init_obj.get_moof_mdat_free_data(v_counter, v_counter_time,
            #                                                  data_frame_raw)
            #     else:
            #         _data = init_obj.get_moof_mdat_free_data(v_counter, v_counter_time,
            #                                                  data_frame_i)
            # else:
            #     _data = init_obj.get_moof_mdat_free_data(v_counter, v_counter_time,
            #                                              data_frame_raw)

            yield _data

    return Response(return_fun(), mimetype='video/mp4')


def process_clean_fun():
    print_to_logger("process clean fun start ....", time.time())
    while 1:
        for child in psutil.Process(os.getpid()).children(recursive=True):
            try:
                if child.status() in (psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD):
                    child.send_signal(9)
                    child.kill()
                    child.wait(1)
            except Exception as e:
                print_to_logger("process clean fun error", str(e))
        time.sleep(2)


if __name__ == '__main__':
    dash_port = os.environ.get('DASH_PORT', None) or 8209
    redis_url = os.environ.get("REDIS_URL", 'redis://127.0.0.1:6379/9')
    # 进程title设置
    setproctitle.setproctitle("ulldash_server")
    try:
        redis_con = redis.Redis.from_url(redis_url) # .ping()
        assert redis_con.ping() == True
        # 删除原有数据
        redis_con.flushdb()
    except:
        raise Exception("redis 无法连接！" + redis_url)
    print(f'ulldash_server start {dash_port}..', time.time())
    print("redis_url", redis_url)
    for k,v in dict_info.items():
        print(f"chan{k} {v[0]}x{v[1]}: /ulldash/{k}/main.mpd")
    my_pid = os.getpid()
    import psutil
    try:
        for child in psutil.Process(1).children(recursive=True):
            if child.name().startswith("dash_rtmp_chan"):
                try:
                    child.kill()
                    child.wait(1)
                except:
                    pass
    except:
        pass
    setproctitle.setproctitle("ull-dash-main")
    my_pid = os.getpid()
    for stream_index in range(4):
        i = stream_index
        print("start rtmp server", f'/live/chan{i}')
        process_task.run_task(_av_rtmp.av_recv_function, args=[stream_index,
                                                               f'{ 8010+i }',
                                                                f'/live/chan{i}',
                                                                hashlib.md5(f'/live/chan{i}'.encode('utf-8')).hexdigest()[:10],
                                                                redis_url,
                                                                f"dash_rtmp_chan{i}",
                                                                my_pid
                                                                ])
    thread_1 = threading.Thread(target=process_clean_fun, daemon=True)
    thread_1.start()

    # server.start()
    from gevent.pywsgi import WSGIServer
    http_server = WSGIServer(('', dash_port), app)
    # http_server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF,
    #                               1024 * 1024 * 32)
    http_server.serve_forever()
