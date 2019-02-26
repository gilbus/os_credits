FROM python:3.7-slim as builder
WORKDIR /code
ADD pyproject.toml poetry.lock /code/
ADD os_credits /code/os_credits
# no virtual necessary for building a wheel but would be create nevertheless
RUN pip install poetry && poetry config settings.virtualenvs.create false && poetry build -f wheel


FROM python:3.7-slim
ARG OS_CREDITS_VERSION
ARG WHEEL_NAME=os_credits-$OS_CREDITS_VERSION-py3-none-any.whl
ENV CREDITS_PORT 80
ENV CREDITS_HOST 0.0.0.0
COPY --from=builder /code/dist/$WHEEL_NAME /tmp/

RUN apt update && apt install -y gcc
RUN pip install --no-cache /tmp/$WHEEL_NAME && rm /tmp/$WHEEL_NAME

CMD os-credits --version
