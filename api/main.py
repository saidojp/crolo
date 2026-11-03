from fastapi import FastAPI, Depends, HTTPException, status  # pyright: ignore[reportMissingImports]

from fastapi.security import OAuth2PasswordRequestForm

from datetime import timedelta

from auth import (

    authenticate_user, create_access_token, get_current_active_user,

    fake_users_db, ACCESS_TOKEN_EXPIRE_MINUTES

)

from models import User

app = FastAPI(title="Crolo")


@app.get("/")
def read_root():
    return {"message": "Welcome to Crolo"}

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # authenticate the user using the provided username and password
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
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