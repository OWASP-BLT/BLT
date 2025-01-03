release: python manage.py migrate  --noinput
#web: newrelic-admin run-program bin/start-pgbouncer uvicorn blt.asgi:application --host 0.0.0.0 --port ${PORT}
web: gunicorn blt.wsgi --log-file - --workers 2 --worker-class gthread --threads 2 --timeout 120