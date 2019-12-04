#!/usr/bin/python3

import audioop
import json
import math
import re
import sys
import time
import threading
import wave

from bottle import get, redirect, response, route, run, static_file, template
from bottle.ext.websocket import GeventWebSocketServer
from bottle.ext.websocket import websocket
from pymumble_py3 import Mumble
from pymumble_py3.callbacks import PYMUMBLE_CLBK_SOUNDRECEIVED
from pymumble_py3.constants import PYMUMBLE_CONN_STATE_NOT_CONNECTED

from prometheus_client import generate_latest, REGISTRY, Gauge, Histogram


class MumbleChannelStats:
    def __init__(self, server, channel, nick='meter@{channel}',
                 peakinterval=.3, buffertime=1., debug=False):
        self.channelname = channel
        self.nick = nick.format(channel=channel)
        self.mumble = Mumble(server, self.nick, password='somepassword',
                             debug=debug)
        self.mumble.set_application_string(
            'Audio Meter for Channel {}'.format(channel))
        self.mumble.callbacks.set_callback(PYMUMBLE_CLBK_SOUNDRECEIVED,
                                           self.sound_received_handler)
        self.mumble.set_receive_sound(1)
        self.mumble.start()
        self.mumble.is_ready()

        if self.channelname is not 'root':
            self.channel = self.mumble.channels.find_by_name(self.channelname)
            self.channel.move_in()

        self.buffer = bytearray()
        self.buffertime = buffertime
        self.rate = 48000
        self.bytespersample = 2
        self.maxvalue = math.pow(2, self.bytespersample * 8 - 1) - 1
        self.buffersize = int(self.rate * self.buffertime * self.bytespersample)
        self.peak = -99
        self.rms = -99
        self.rmsbytes = -int(.3 * self.rate) * self.bytespersample
        self.samples = 0
        self.lastpeak = time.monotonic()
        self.peakinterval = peakinterval
        self.last = -sys.maxsize
        self.users = 0

    def get_channels(self):
        return self.mumble.channels.values()

    def dBFS(self, value):
        if value < 1:
            value = 1
        return 20 * math.log10(value / self.maxvalue) + 3

    def sound_received_handler(self, user, sound):
        self.add_sound(sound.pcm)

    def add_sound(self, sound):
        self.last = time.monotonic()
        self.buffer.extend(sound)
        self.buffer = self.buffer[-self.buffersize:]
        self.samples += len(sound) / self.bytespersample

    def update_stats(self):
        now = time.monotonic()
        if now > self.lastpeak + self.peakinterval:
            self.lastpeak = now
            self.peak = -99
        if now - self.last > 0.1:
            self.peak = self.rms = -90.0
        else:
            self.rms = self.dBFS(
                audioop.rms(self.buffer[-self.rmsbytes:], self.bytespersample))
            peak = self.dBFS(audioop.max(self.buffer, self.bytespersample))
            self.peak = max(peak, self.peak)
        self.users = len(self.channel.get_users())

    def is_alive(self):
        return self.mumble.is_alive()

    def __str__(self):
        return f'<MumbleChannelStats channel={self.channelname} rms={self.rms} peak={self.peak} users={self.users}>'

    def __repr__(self):
        return f'channel={self.channelname} rms={self.rms} peak={self.peak} users={self.users}'


class MumbleStats():
    def __init__(self, server):
        self.server = server
        self.stats = {}
        self.wsstats_clients = []
        self.metrics = {}
        self.running = True
        root = MumbleChannelStats(self.server, 'root')
        self.channels = [c['name'] for c in list(root.get_channels())[1:]]
        self.mumble_close(root)

    def get_stats(self):
        r = {}
        for mumble_channel_stats in mumble_stats.stats.values():
            s = {}
            s['rms'] = mumble_channel_stats.rms
            s['peak'] = mumble_channel_stats.peak
            s['users'] = mumble_channel_stats.users
            r[mumble_channel_stats.channel['name']] = s
        return r

    def get_prometheus_metric(self, n, type, doc, **kwargs):
        if n not in self.metrics:
            self.metrics[n] = type(n, doc, **kwargs)
        return self.metrics[n]

    def update_prometheus_metrics(self, stats):
        buckets = (-36, -30, -24, -18, -12, -6, -3, 0, 3)
        for (name, v) in stats.items():
            m = self.get_prometheus_metric(
                'mumble_level', Histogram,
                'audio level in dBFS, either root-mean-square or peak',
                labelnames=['channel', 'level'],
                unit='dBFS', buckets=buckets)
            m.labels(channel=name, level='rms').observe(v['rms'])
            m.labels(channel=name, level='peak').observe(v['peak'])
            m = self.get_prometheus_metric(
                'mumble_users', Gauge,
                'number of users connected',
                labelnames=['channel'])
            m.labels(channel=name).set(v['users'])

    def collect_stats(self):
        global wsstats_clients
        for channel in self.channels:
            print('Connecting to {}...'.format(channel))
            self.stats[channel] = MumbleChannelStats(self.server, channel)
        while self.running:
            for channel in self.channels:
                if not self.stats[channel].is_alive():
                    print('{} is not alive anymore'.format(channel))
                    return
                self.stats[channel].update_stats()
            stats = self.get_stats()
            self.update_prometheus_metrics(stats)
            wsjson = json.dumps(stats)
            for ws in self.wsstats_clients:
                ws.send(wsjson)
            time.sleep(.1)
        for channel in self.channels:
            self.mumble_close(self.stats[channel])

    def thread(self):
        self.thread = threading.Thread(target=self.collect_stats, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()

    def mumble_close(self, mumble):
        if mumble.is_alive():
            mumble.mumble.connected = PYMUMBLE_CONN_STATE_NOT_CONNECTED
            mumble.mumble.control_socket.close()

    def __repr__(self):
        return str({'server': self.server})


@route('/')
def to_index():
    redirect('/mumblestats/')


@route('/mumblestats/')
def get_index():
    params = {}
    params['server'] = mumble_stats.server
    return template('index', params)


@route('/mumblestats/static/<filename>')
def server_static(filename):
    return static_file(filename, root='static')


@route('/mumblestats/stats')
def get_stats():
    global mumble_stats
    return mumble_stats.get_stats()


@get('/mumblestats/wsstats', apply=[websocket])
def ws_stats(ws):
    global mumble_stats
    mumble_stats.wsstats_clients.append(ws)
    ws.send(json.dumps(mumble_stats.get_stats()))
    while True:
        if ws.receive() is None:
            break
    mumble_stats.wsstats_clients.remove(ws)


@route('/mumblestats/metrics')
def metrics():
    response.content_type = 'text/plain'
    return generate_latest(REGISTRY)


# @route('/mumblestats/objgraph')
# def dump_objgraph():
#     global mumble_stats
#     import objgraph
#     import random
#     objgraph.show_growth(limit=10)
#     # objgraph.show_refs(mumble_stats, filename='mumble_stats.png')
#     q = random.choice(objgraph.by_type('SoundQueue'))
#     print(f'len(queue)={len(q.queue)}')
#     objgraph.show_chain(
#         objgraph.find_backref_chain(q, objgraph.is_proper_module),
#         filename='SoundQueue.png')
#     # objgraph.show_chain(
#     #     objgraph.find_backref_chain(
#     #         random.choice(objgraph.by_type('SoundChunk')),
#     #         objgraph.is_proper_module),
#     #     filename='SoundChunk.png')
#     return 'done'


def main():
    global mumble_stats
    mumble_stats = MumbleStats(sys.argv[1])
    mumble_stats.thread()
    try:
        run(host='localhost', port=8080, server=GeventWebSocketServer,
            debug=True)
    except KeyboardInterrupt:
        mumble_stats.stop()
        print('stopping...')
        time.sleep(1)


if __name__ == "__main__":
    main()
