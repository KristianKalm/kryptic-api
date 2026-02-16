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

## Running

```bash
pip install fastapi uvicorn python-multipart pyotp
uvicorn app.main:app --reload
```

## Swagger Docs

Access the docs at `http://localhost:8000/docs`
