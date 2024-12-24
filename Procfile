release: python manage.py migrate  --noinput
web: uvicorn blt.asgi:application --host 0.0.0.0 --port ${PORT}
