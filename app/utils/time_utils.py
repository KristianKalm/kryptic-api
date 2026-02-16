from datetime import datetime, timezone


def get_utc_timestamp():
    return int(datetime.now(timezone.utc).timestamp())
