FROM python:3.11-slim

WORKDIR /app

COPY ./app /app/app
COPY ./default_conf.json /app/default_conf.json
COPY ./entrypoint.sh /app/entrypoint.sh

RUN pip install fastapi uvicorn python-multipart pyotp slowapi fast_captcha pillow && \
    chmod +x /app/entrypoint.sh

EXPOSE 11213

VOLUME ["/app/appData"]

ENTRYPOINT ["/app/entrypoint.sh"]