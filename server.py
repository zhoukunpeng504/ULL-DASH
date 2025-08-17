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
from flask import Flask
import mimetypes,hashlib,subprocess
import requests
import random,sys
import jinja2
from flask import Response
import flask_cors


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

app = Flask(__name__)
flask_cors.CORS(app)

dict_info = {"0":("1280","720"),
                 "1":("1920","1080"),
                 "2":("2560","1440"),
                 "3":("3840","2160"),}

# 如： /ulldash/0/main.mpd   0 对应720p
@app.route("/ulldash/<path:stream_index>/main.mpd")
def mpd_index(stream_index:str):
    global dict_info
    request = flask.request
    with open("./template.mpd", "r") as f:
        template = jinja2.Template(f.read())
    width, height = dict_info[stream_index]
    now = datetime.datetime.now()
    publishTime = now.strftime("%Y-%m-%dT%H:%M:%SZ")  # 2025-08-13T02:02:03Z
    utc_value = now.strftime("%Y-%m-%dT%H:%M:%S.%fZ") # 2025-08-13T02:02:03.789000Z
    #print(template)
    response_content = template.render(width=width, height=height, stream_index=stream_index,
                                       publishTime=publishTime, utc_value=utc_value)
    return Response(response_content, content_type="application/dash+xml")


@app.route("/chan<int:stream_index>_init.mp4")
def chan_init(stream_index:int):
    # 一共4个通道
    # 具体配置如上 dict_info中所示
    # profile 按照HIGH
    # level  按照4.2
    # pps 和 sps 从推流时的写入的内存参数中获取， 如果获取不到，则返回404
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
    return resp


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
