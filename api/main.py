from fastapi import FastAPI, Depends, HTTPException, status  # pyright: ignore[reportMissingImports]
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from typing import cast
from sqlalchemy.orm import Session
import crud
from database import get_db
from auth import (
   create_access_token, get_current_active_user, ACCESS_TOKEN_EXPIRE_MINUTES
)
from models import User, UserCreate
from routers import decks, sessions

app = FastAPI(title="Crolo")

app.include_router(decks.router)
app.include_router(sessions.router)
app.include_router(sessions.deck_router)


@app.get("/")
def read_root():
    return {"message": "Welcome to Crolo"}


@app.post("/register/", response_model=User)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = crud.create_user(db=db, user=user)
    return User(
        id=cast(int, new_user.id),
        username=cast(str, new_user.username),
        email=cast(str, new_user.email),
        full_name=cast(str, new_user.full_name),
        disabled=not cast(bool, new_user.is_active),
        roles=[cast(str, role.name) for role in new_user.roles])


@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Authenticate user and return access token."""
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@app.get("/protected")
async def protected_route(current_user: User = Depends(get_current_active_user)):
    return {"message": f"Hello {current_user.full_name}, this is a protected route!"}
