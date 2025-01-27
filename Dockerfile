FROM python:3.7-alpine as builder

ADD src /code/src
ADD pyproject.toml poetry.lock /code/
WORKDIR /code
RUN pip install poetry && poetry build -f wheel

# by using a build container we prevent us from carrying around poetry
# alongside its dependencies
FROM python:3.7-alpine
ARG OS_CREDITS_VERSION
ARG WHEEL_NAME=os_credits-$OS_CREDITS_VERSION-py3-none-any.whl
EXPOSE 80
ENV CREDITS_PORT 80
ENV CREDITS_HOST 0.0.0.0
COPY --from=builder /code/dist/$WHEEL_NAME /tmp/

# wget to perform healthcheck against /ping endpoint
RUN apk update && apk --no-cache add gcc wget linux-headers musl-dev \
	&& pip install --no-cache /tmp/$WHEEL_NAME \
	&& rm /tmp/$WHEEL_NAME

CMD os-credits
