import datetime
from fastapi import APIRouter, Request, Query
from typing import Optional, List
from ..internal.ayame_query import ayame_query
router = APIRouter(
    prefix="/search",
    tags=["search"],
    responses={404: {"description": "Not found"}},
)


def today(offset_day=0):
    td = datetime.timedelta(days=offset_day)
    JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
    dt_now = datetime.datetime.now(JST) + td
    return dt_now.strftime('%Y-%m-%d')


def result_filter(docs, pageid):

    if pageid:
        result = [doc["id"] for doc in docs if "id" in doc]
    else:
        # リスト内包表記が長すぎるので普通に表記
        result = []
        for doc in docs:
            if "metatitle" in doc:
                result.append(doc["metatitle"])
            elif "fullname" in doc:
                result.append(doc["fullname"])
    return result


@router.get("/tag")
async def tag(tags: Optional[List[str]] = Query(None),
              pageid: Optional[bool] = False):
    """
    タグによる部分一致and検索
    戻り値はid
    """
    if tags is None:
        return []
    _filter = {"_id": 0, "id": 1, "metatitle": 1, "fullname": 1}
    result = await ayame_query.tag_partial_match(tags, _filter)
    return result_filter(result, pageid)


@router.get("/create_at")
async def create_at(_from: Optional[str] = Query(today(-30)),
                    _to: Optional[str] = Query(today()),
                    pageid: Optional[bool] = False):
    _filter = {"_id": 0, "id": 1, "metatitle": 1, "fullname": 1}
    result = await ayame_query.create_at_range_match(_from, _to, _filter)
    return result_filter(result, pageid)


@router.get("/title")
async def title(title: Optional[str] = Query(None),
                pageid: Optional[bool] = False):
    """
    fullnameもしくはmetatitleによる部分一致検索\n
    戻り値:fullnameとmetatitle(優先)の複合 もしくは pageid
    """
    _filter = {"_id": 0, "id": 1, "metatitle": 1, "fullname": 1}
    result = await ayame_query.title_partial_match(title, _filter)
    return result_filter(result, pageid)
