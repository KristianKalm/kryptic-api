from typing import Optional
from pydantic import BaseModel, field_validator

from app.utils.validation import is_valid_username


class Encrypted(BaseModel):
    ciphertext: str
    iv: str
    salt: str


class User(BaseModel):
    username: str
    password: str
    timestamp: Optional[int] = None  # Unix timestamp milliseconds UTC
    seed: Optional[Encrypted] = None
    public_key: Optional[str] = None
    private_key: Optional[Encrypted] = None
    pin: Optional[str] = None
    token_name: Optional[str] = None

    @field_validator("username")
    @classmethod
    def _validate_username(cls, value: str) -> str:
        if not is_valid_username(value):
            raise ValueError("invalid username")
        return value


class RegisterRequest(User):
    captcha_id: str
    captcha_text: str
