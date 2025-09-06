# syntax=docker/dockerfile:1.7
FROM python:3.13-trixie

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN set -eux; \
  apt-get update; \
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    libgirepository-2.0-dev \
    libcairo-gobject2 \
    gir1.2-pango-1.0 \
    libsm6 libxext6 libxrender1 libgl1 \
  ; \
  rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.lock /app/requirements.lock
RUN pip install --no-cache-dir -r requirements.lock

RUN mkdir -p /usr/local/share/fonts &&\
    wget -O /usr/local/share/fonts/AppleColorEmoji.ttf https://github.com/samuelngs/apple-emoji-linux/releases/latest/download/AppleColorEmoji.ttf &&\
    fc-cache -f -v

COPY . /app

ARG APP_UID=1000
ARG APP_GID=1000
RUN set -eux; \
    mkdir /app/.insightface; \
    groupadd -g "${APP_GID}" appuser || groupmod -n appuser "$(getent group "${APP_GID}" | cut -d: -f1)" || true; \
    id -u "${APP_UID}" >/dev/null 2>&1 || useradd -u "${APP_UID}" -g "${APP_GID}" -d /app -s /usr/sbin/nologin appuser; \
    chown -R "${APP_UID}:${APP_GID}" /app

USER appuser

ENTRYPOINT ["/usr/local/bin/python", "/app/main.py"]
