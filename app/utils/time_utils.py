from datetime import datetime, timezone


def get_utc_timestamp():
    return int(datetime.now(timezone.utc).timestamp())


def get_utc_timestamp_ms():
    return int(datetime.now(timezone.utc).timestamp() * 1000)
