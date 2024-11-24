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
RUN poetry install
RUN pip install opentelemetry-api opentelemetry-instrumentation

# Install dos2unix
RUN apt-get update && apt-get install -y dos2unix

# Add entrypoint

COPY entrypoint.sh /entrypoint.sh
RUN dos2unix .env Dockerfile docker-compose.yml entrypoint.sh ./blt/settings.py
RUN chmod +x /entrypoint.sh


ENTRYPOINT [ "./entrypoint.sh" ]
CMD [ "poetry", "run", "python", "manage.py", "runserver", "0.0.0.0:8000" ]