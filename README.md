# Kryptic Api

A FastAPI-based backend with user registration, login, and file listing.

## Endpoints

- **POST /register** - Register a user
- **POST /login** - Login and get a token
- **GET /index** - List files under user directory (requires token)

## File Structure

- `app/main.py` - App entry point
- `app/routes/` - Route handlers
- `app/utils/` - Helper modules
- `user/` - User data

## Running Locally

```bash
pip install fastapi uvicorn python-multipart pyotp
uvicorn app.main:app --reload
```

## Running with Docker

```bash
docker build -t simple-user-api .
docker run -p 8000:8000 simple-user-api
```

## Swagger Docs

Access the docs at `http://localhost:8000/docs`
