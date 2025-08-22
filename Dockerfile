FROM opensuse/leap:15.6
RUN zypper -n in ImageMagick python311 Mesa-libGL1 libgthread-2_0-0 &&\
    zypper -n clean --all && \
    rm -rf /var/cache/zypp/* &&\
    python3.11 -m ensurepip
COPY requirements.txt /app/
RUN python3.11 -m pip install -r /app/requirements.txt
COPY . /app/
WORKDIR /app
ENTRYPOINT ["/usr/bin/python3.11", "/app/main.py"]
