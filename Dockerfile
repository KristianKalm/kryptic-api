FROM python:3.11-slim

WORKDIR /app

COPY ./app /app/app
COPY ./conf.json /app/config/conf.json

RUN pip install fastapi uvicorn python-multipart pyotp slowapi

EXPOSE 11213

VOLUME ["/app/appData", "/app/config"]

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-11213}