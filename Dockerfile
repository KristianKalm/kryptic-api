FROM python:3.11-slim

WORKDIR /app

COPY ./app /app/app
COPY ./conf.json /app/conf.json

RUN pip install fastapi uvicorn python-multipart pyotp slowapi

EXPOSE 8000

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-11213}