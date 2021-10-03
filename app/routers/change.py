import datetime
from fastapi import APIRouter, Request, Query
from typing import Optional, List
from ..internal.ayame_query import ayame_query
router = APIRouter(
    prefix="/change",
    tags=["change"],
    responses={404: {"description": "Not found"}},
)


@router.get("/pageid")
async def pageid_match(title: Optional[str] = Query("SCP-173 - 彫刻 - オリジナル")):
    """
    fullnameもしくはmetatitleをpageidに変換します。
    """
    _filter = {"_id": 0, "id": 1, "metatitle": 1, "fullname": 1}
    result = await ayame_query.title_perfect_match(title, _filter)
    if result is None:
        return None
    else:
        return result["id"]
