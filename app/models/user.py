from typing import Optional
from pydantic import BaseModel


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
