FROM python:slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED 1
ENV VIRTUAL_ENV=/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install packages needed to run your application (not build deps):
# We need to recreate the /usr/share/man/man{1..8} directories first because
# they were clobbered by a parent image.

RUN set -ex \
    && RUN_DEPS=" \
        libfreetype6 \
        libfribidi-bin \
        libharfbuzz-bin \
        libjpeg62-turbo \
        liblcms2-2 \
        libopenjp2-7 \
        libtiff5 \
        libwebp6 \
        libxcb1 \
        libexpat1-dev \
        postgresql-client \
        zlib1g \
    " \
    && apt-get update && apt-get install -y --no-install-recommends $RUN_DEPS \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /
COPY requirements requirements

#        tcl8.6-dev \
#        tk8.6-dev \
RUN set -ex \
    && BUILD_DEPS=" \
        build-essential \
        libfreetype6-dev \
        libfribidi-dev \
        libharfbuzz-dev \
        libjpeg62-turbo-dev \
        liblcms2-dev \
        libopenjp2-7-dev \
        libpq-dev \
        libtiff5-dev \
        libwebp-dev \
        libxcb1-dev \
        libexpat1-dev \
        zlib1g-dev \
    " \
    && apt-get update && apt-get install -y --no-install-recommends $BUILD_DEPS \
    && python3 -m venv $VIRTUAL_ENV \
    && pip install -U pip wheel\
    && pip install --no-cache-dir -r /requirements.txt \
    && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false $BUILD_DEPS \
    && rm -rf /var/lib/apt/lists/*

ARG USERNAME=worker
ARG APP_NAME=blogsite
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Create the user
RUN groupadd --gid $USER_GID $USERNAME && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME

# create media dir
RUN mkdir -p /opt/g10f/$APP_NAME/htdocs/media
RUN chown $USERNAME:$USERNAME /opt/g10f/$APP_NAME/htdocs/media

WORKDIR /opt/g10f/$APP_NAME/apps
COPY apps .
COPY Docker/gunicorn.conf.py ./gunicorn.conf.py

RUN chown -R $USERNAME: $VIRTUAL_ENV
RUN chown -R $USERNAME: /opt/g10f

USER $USERNAME
ARG SECRET_KEY=dummy
RUN ./manage.py collectstatic

ENV DJANGO_SETTINGS_MODULE=$APP_NAME.settings.production

ENTRYPOINT ["./docker-entrypoint.sh"]

# Start gunicorn
CMD ["gunicorn", "$APP_NAME.wsgi:application", "--bind 0.0.0.0:8000", "-w", "2"]
EXPOSE 8000
