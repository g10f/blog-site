#!/usr/bin/env bash
set -ef


if [ "$DJANGO_MIGRATE" = "on" ]; then
	./manage.py migrate --noinput
fi

# a superuser is only created in a database without users, not on every start
if [ "$DJANGO_CREATE_SUPERUSER" = "on" ]; then
  user_count=$(./manage.py user_count)

  if [[ $user_count -eq 0 ]]; then
    ./manage.py createsuperuser --noinput
  fi
fi

exec "$@"
