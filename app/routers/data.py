import datetime
from fastapi import APIRouter, Request, Query
from typing import Optional, List
from ..internal.ayame_query import ayame_query
router = APIRouter(
    prefix="/data",
    tags=["data"],
    responses={404: {"description": "Not found"}},
)


def today():
    JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
    dt_now = datetime.datetime.now(JST)
    return dt_now.strftime('%Y-%m-%d')


@router.get("/pageid")
async def pageid_match(pageid: Optional[str] = Query("19439882"),
                       date: Optional[str] = Query(None)):
    """
    pageidに完全一致する対象のデータを返します。\n
    日付が指定されていない・形式が間違っている場合最新データを返します。\n
    正しく日付が指定されているがデータが存在しない場合、nullを返します。
    """
    return await ayame_query.pageid_match(pageid, date)
