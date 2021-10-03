from fastapi import FastAPI
from .routers import search
from .routers import data
from .routers import change

app = FastAPI()
app.include_router(search.router)
app.include_router(data.router)
app.include_router(change.router)


@app.get("/")
async def root():
    return {"message": "Hello Bigger Applications!"}
