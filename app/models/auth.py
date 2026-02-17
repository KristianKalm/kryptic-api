from pydantic import BaseModel


class Auth(BaseModel):
    username: str
    app: str
    token_id: str
