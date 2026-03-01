#!/bin/sh

if [ ! -f /app/appData/conf.json ]; then
    echo "conf.json not found, copying default..."
    cp /app/default_conf.json /app/appData/conf.json
fi

exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-11213}
