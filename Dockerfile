FROM opensuse/leap:15.6
RUN zypper -n in ImageMagick \
        python311-devel \
        cairo-devel \
        gobject-introspection-devel \
        typelib-1_0-Pango-1_0 \
        girepository-1_0 \
        Mesa-libGL1 \
        libgthread-2_0-0 \
        noto-coloremoji-fonts \
        dejavu-fonts \
        gcc-c++ &&\
    zypper -n clean --all && \
    rm -rf /var/cache/zypp/* &&\
    python3.11 -m ensurepip
COPY requirements.txt /app/
RUN python3.11 -m pip install -r /app/requirements.txt
COPY . /app/
WORKDIR /app
ENTRYPOINT ["/usr/bin/python3.11", "/app/main.py"]
