FROM python:3.7-slim as builder
WORKDIR /code
ADD pyproject.toml poetry.lock /code/
ADD os_credits /code/os_credits
# no virtual necessary for building a wheel but would be create nevertheless
RUN pip install poetry && poetry config settings.virtualenvs.create false && poetry build -f wheel


FROM python:3.7-slim
ARG OS_CREDITS_VERSION
ARG WHEEL_NAME=os_credits-$OS_CREDITS_VERSION-py3-none-any.whl
EXPOSE 80
ENV CREDITS_PORT 80
ENV CREDITS_HOST 0.0.0.0
COPY --from=builder /code/dist/$WHEEL_NAME /tmp/

# wget to perform healthcheck against /ping endpoint
RUN apt-get update && apt-get install -y gcc wget  && apt-get clean
RUN pip install --no-cache /tmp/$WHEEL_NAME && rm /tmp/$WHEEL_NAME

CMD os-credits
