release: python manage.py migrate  --noinput
web: bin/start-pgbouncer uvicorn blt.asgi:application --host 0.0.0.0 --port ${PORT}
