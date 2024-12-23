release: python manage.py migrate  --noinput
web: gunicorn blt.wsgi --log-file - --workers 2 --worker-class gthread --threads 2 --timeout 120
