from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from .routers import search
from .routers import data
from .routers import change
from .routers import system
from .routers import json_download

from .routers import tags_metadata


app = FastAPI(openapi_tags=tags_metadata.tags_metadata)
app.include_router(search.router)
app.include_router(data.router)
app.include_router(change.router)
app.include_router(system.router)
app.include_router(json_download.router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
# プロキシヘッダー読み取り
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")


@app.get("/")
async def root():
    return {"message": "Hello Bigger Applications!"}
