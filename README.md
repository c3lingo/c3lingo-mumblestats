# c3lingo-mumblestats

A Mumble client that collects stats on the users and the audio of all channels that can be publicly joined. The stats are made available over HTTP and Websocket. There is an HTML client that displays the stats live.

## Building c3lingo-mumblestats

Set up a virtual Python environment and install the prerequites. You probably need at least Python 3.6.

```bash
$ python3 -m venv .venv
$ source .venv/bin/activate
(.venv) $ python mumblestats.py
```

The server is running on [`localhost:8080`](http://localhost:8080/).
