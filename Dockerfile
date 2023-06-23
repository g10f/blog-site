FROM python

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED 1
ENV VIRTUAL_ENV=/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY requirements.txt /
COPY requirements requirements

RUN set -ex \
    && python3 -m venv $VIRTUAL_ENV \
    && pip install -U pip wheel\
    && pip install --no-cache-dir -r /requirements.txt

ARG USERNAME=worker
ARG PROJ_NAME=blog-site
#ARG APP_NAME=blogsite
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Create the user
RUN groupadd --gid $USER_GID $USERNAME && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME

# create media dir
RUN mkdir -p /opt/g10f/$PROJ_NAME/htdocs/media
RUN chown $USERNAME:$USERNAME /opt/g10f/$PROJ_NAME/htdocs/media

WORKDIR /opt/g10f/$PROJ_NAME/apps
COPY apps .
COPY Docker/gunicorn.conf.py ./gunicorn.conf.py

RUN chown -R $USERNAME: $VIRTUAL_ENV
RUN chown -R $USERNAME: /opt/g10f

USER $USERNAME
ARG SECRET_KEY=dummy
RUN ./manage.py collectstatic

ENV DJANGO_SETTINGS_MODULE=blogsite.settings.production

ENTRYPOINT ["./docker-entrypoint.sh"]

# Start gunicorn
CMD ["gunicorn", "blogsite.wsgi:application", "--bind 0.0.0.0:8000", "-w", "2"]
EXPOSE 8000
