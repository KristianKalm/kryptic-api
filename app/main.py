from urllib.request import Request

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from app.routes import register, files, usage, login, tokens, info, file, ota, account
from app.utils.conf_utils import load_conf

load_conf()

app = FastAPI()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
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
