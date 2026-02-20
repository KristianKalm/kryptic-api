from urllib.request import Request

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

from app.routes import register, files, usage, login, tokens, info, file, ota, account
from app.utils.conf_utils import load_conf

load_conf()

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"message": exc.errors()},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # http://localhost:55432
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# No auth required
app.include_router(info.router)

# Auth
app.include_router(register.router)
app.include_router(login.router)

# Token authorized requests
app.include_router(tokens.router)
app.include_router(file.router)
app.include_router(files.router)
app.include_router(usage.router)
app.include_router(ota.router)
app.include_router(account.router)
