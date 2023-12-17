FROM python:buster

RUN apt-get -y update && \
    apt-get install -y libopus-dev portaudio19-dev pulseaudio && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt && \
    rm -f /tmp/requirements.txt

RUN useradd -ms /bin/bash app
USER app
WORKDIR /home/app
COPY --chown=app mumblestats.py ./
COPY --chown=app index.tpl ./
COPY --chown=app static ./static

CMD ["/usr/local/bin/python", "mumblestats.py", "mumble.c3lingo.org"]
