# Build stage: compiles the Python packages into /venv. Only psycopg-c is built from source,
# the other packages come as wheels with their libraries included.
FROM python:3.14.9-slim AS build

RUN set -ex \
    && apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/base.txt /requirements.txt
RUN python3 -m venv /venv \
    && /venv/bin/pip install --no-cache-dir -r /requirements.txt


FROM python:3.14.9-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Runtime packages: libpq5 for psycopg, media-types for the mimetypes module,
# postgresql-client and procps for working in the container
RUN set -ex \
    && apt-get update && apt-get install -y --no-install-recommends libpq5 media-types postgresql-client procps \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /venv /venv

ARG USERNAME=worker
ARG PROJ_NAME=blog-site
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Create the user
RUN groupadd --gid $USER_GID $USERNAME && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME

# The venv and the code belong to root. The user only writes the media files and, with collectstatic
# (also in the theme images), the static files.
RUN mkdir -p /opt/g10f/$PROJ_NAME/htdocs/media /opt/g10f/$PROJ_NAME/htdocs/static \
    && chown $USERNAME:$USERNAME /opt/g10f/$PROJ_NAME/htdocs/media /opt/g10f/$PROJ_NAME/htdocs/static

WORKDIR /opt/g10f/$PROJ_NAME/apps
COPY apps .

ENV DJANGO_SETTINGS_MODULE=blogsite.settings.production

USER $USERNAME
RUN ./manage.py collectstatic --noinput

ENTRYPOINT ["./docker-entrypoint.sh"]

# Start gunicorn
CMD ["gunicorn", "blogsite.wsgi:application", "-b", "0.0.0.0:8000", "--forwarded-allow-ips", "*"]
EXPOSE 8000
