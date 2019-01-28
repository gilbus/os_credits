FROM python:3.7-alpine

ADD src /code/src
ADD config/credits.toml /etc/credits.toml
ADD pyproject.toml poetry.lock /code/
WORKDIR /code
# pip>19 is required for pyproject.toml
RUN pip install --no-cache --upgrade pip
# RUN pip install --no-cache .
# usage of --no-cache does lead to breakage currently
# see https://github.com/pypa/pip/issues/6197
RUN pip install .

ENV CREDITS_PORT 80
ENV CREDITS_HOST 0.0.0.0

EXPOSE 80
CMD python -m aiohttp.web -H $CREDITS_HOST -P $CREDITS_PORT os_project_usage_processor.main:app_init
