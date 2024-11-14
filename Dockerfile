FROM python:3.11.2

ENV PYTHONUNBUFFERED 1
RUN mkdir /blt
WORKDIR /blt
COPY . /blt


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

RUN pip install poetry 
RUN poetry config virtualenvs.create false
RUN poetry lock
RUN poetry install
RUN pip install opentelemetry-api opentelemetry-instrumentation


RUN python manage.py collectstatic --noinput
CMD python manage.py migrate && \
    python manage.py create_superuser && \
    python manage.py loaddata website/fixtures/initial_data.json 
