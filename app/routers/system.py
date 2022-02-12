from fastapi import APIRouter, Request, Query
from typing import Optional, List
from ..internal.ayame_query import ayame_query
from ..internal.ayame_update import ayame_update
router = APIRouter(
    prefix="/system",
    tags=["system"],
    responses={404: {"description": "Not found"}},
)


@router.on_event("startup")
async def on_startup():
    pass
    # print("hoge")


@router.get("/update_database")
async def update_database():
    return await ayame_update.update_database()


@router.get("/convert_database")
async def convert_database():
    await ayame_update.convert_database_type()
