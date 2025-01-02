release: python manage.py migrate  --noinput
web: newrelic-admin run-program bin/start-pgbouncer uvicorn blt.asgi:application --host 0.0.0.0 --port ${PORT}
