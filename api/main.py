from fastapi import FastAPI, Depends
from auth import authenticate_user

from fastapi import FastAPI

app = FastAPI(title="Crolo")


@app.get("/")
def read_root():
    return {"message": "Welcome to Crolo"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}

@app.get("/secured")

async def protected_route(current_user: str = Depends(authenticate_user)):

    return {"message": f"Hello {current_user}, this is a protected route!"}