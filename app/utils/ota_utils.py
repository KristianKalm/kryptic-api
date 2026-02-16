import pyotp


def generate_ota_key():
    return pyotp.random_base32()


def generate_ota_pin(secret):
    totp = pyotp.TOTP(secret)
    return totp.now()


def verify_ota_pin(secret, pin):
    totp = pyotp.TOTP(secret)
    return totp.verify(pin, valid_window=1)
