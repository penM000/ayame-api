
from fastapi import APIRouter, Request, Query
from fastapi.staticfiles import StaticFiles
from typing import Optional, List
from fastapi.responses import FileResponse
router = APIRouter(
    prefix="/json",
    tags=["json"],
    responses={404: {"description": "Not found"}},
)

"""
@router.get("/data")
async def get_data():

    return FileResponse(
        "ayame/data/data.json",
        media_type='application/octet-stream',
        filename="data.json")
"""

@router.get("/page_ids")
async def get_page_ids():
    return FileResponse(
        "ayame/data/page_ids.json",
        media_type='application/octet-stream',
        filename="page_ids.json")
