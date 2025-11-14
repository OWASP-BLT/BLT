release: python manage.py migrate  --noinput
web: bin/start-pgbouncer uvicorn blt.asgi:application --host 0.0.0.0 --port ${PORT} --workers 1
#web: gunicorn blt.wsgi --log-file - --workers 1 --worker-class gthread --threads 2 --timeout 120
