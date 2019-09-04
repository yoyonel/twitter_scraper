FROM python:3.7-alpine3.9

LABEL description="A python 3.7 image based on Alpine 3.9, with pipenv installed"

RUN pip install --no-cache-dir pip --upgrade && \
    pip install --no-cache-dir pipenv==11.10.0 && \
    rm -rf ~/.cache/pip
