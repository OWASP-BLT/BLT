FROM python:3.8

ENV PYTHONUNBUFFERED 1
RUN mkdir /bugheist
WORKDIR /bugheist
ADD . /bugheist


# Install PostgreSQL dependencies
RUN apt-get update && \
    apt-get install -y postgresql-client libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install pylibmc dependencies
RUN apt-get update && apt-get install -y \
        libmemcached11 \
        libmemcachedutil2 \
        libmemcached-dev \
        libz-dev

RUN pip install pipenv
RUN pipenv install

RUN python manage.py migrate --noinput
RUN python manage.py loaddata website/fixtures/initial_data.json
RUN python manage.py collectstatic
RUN python manage.py initsuperuser

CMD ["python","manage.py","runserver"]