import asyncio
import datetime
import json
import random
import string
import pprint
import copy

import aiofiles
import motor.motor_asyncio
from pymongo import IndexModel, ASCENDING, DESCENDING
from fastapi import FastAPI
# from fastapi.middleware.gzip import GZipMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import items


# アップデートパスワード
update_password = "hello world"


def randomname(n):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))


try:
    with open("/fastapi/password.txt") as f:
        update_password = f.read()
except BaseException:
    update_password = str(randomname(10))
    f = open("/fastapi/password.txt", 'w')
    f.write(update_password)
    f.close()


# docsの説明
tags_metadata = [
    {
        "name": "update",
        "description": "データベース更新時に使用するもので、一般ユーザーは使用できません",
    },
    {
        "name": "id api",
        "description": "pageidを用いるapi",

    },
    {
        "name": "fullname api",
        "description": "fullnameを用いるapi",
    }
]
# fastapiインスタンス作成
app = FastAPI(
    title="ayame api",
    description="This is a very fancy project, with auto docs for the API and everything",
    version="1.0.0",
    openapi_tags=tags_metadata)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,   # 追記により追加
    allow_methods=["*"],      # 追記により追加
    allow_headers=["*"]       # 追記により追加
)
# プロキシヘッダー読み取り
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
##

# タイムゾーン設定
JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')

# システム状態変数
update_status = "NO"
last_update = ""
all_fullname = []
all_id = []

# 状態取得


@app.get("/status")
async def get_status():
    return await items.get_status()

# データベース更新


@app.get("/update", tags=["update"])
async def update(password: str = ""):
    return await items.update()

# fullname
# タグ検索


@app.post("/get_fullname_from_latest_tag_fuzzy_search", tags=["fullname api"])
async def get_fullname_from_latest_tag_fuzzy_search(tags: list = []):
    """
    tagからあいまい検索を行います。少なくとも1つは完全なtagが必要です。\n
    返り値はリストです。\n
    ng ["殿堂","爬虫"]\n
    ok ["殿堂","爬虫類"]\n
    """
    return await items.get_fullname_from_latest_tag_fuzzy_search(tags)

# タグ検索


@app.post("/get_fullname_from_latest_tag_perfect_matching",
          tags=["fullname api"])
async def get_fullname_from_latest_tag_perfect_matching(tags: list = []):
    """
    tagから完全一致検索を行います。tagの要素は完全である必要があります。\n
    返り値はリストです。\n
    ng ["殿堂","爬虫類"]\n
    ok ["殿堂入り","爬虫類"]\n
    """
    return await get_fullname_from_latest_tag_perfect_matching(tags)

# 日時取得


@app.get("/get_dates_from_fullname", tags=["fullname api"])
async def get_dates_from_fullname(fullname: str = "scp-173", _range: int = 7, _page: int = 1):
    """
    取得可能なデータ日時をページ単位で取得します。\n
    返り値はリストです。
    """
    dates = await items.get_date_from_fullname_db(fullname)
    return items.make_page(dates, _range, _page)

# 最新データ取得


@app.get("/get_latest_data_from_fullname", tags=["fullname api"])
async def get_latest_data_from_fullname(fullname: str = "scp-173"):
    """
    最新のデータを取得します。\n
    返り値は辞書です。
    """
    return await items.search_tag_collection.find_one({"fullname": fullname}, {"_id": 0})


# データ取得
@app.get("/get_data_from_fullname_and_date", tags=["fullname api"])
async def get_data_from_fullname_and_date(fullname: str = "scp-173", date: str = "2020-xx-xx"):
    """
    指定された日付のデータを取得します。\n
    返り値は辞書です。該当がなければnullです。
    """
    return items.get_data_from_fullname_and_date(fullname, date)

# rateデータ取得


@app.get("/get_rate_from_fullname_during_the_period", tags=["fullname api"])
async def get_rate_from_fullname_during_the_period(fullname: str = "scp-173", start: str = "2020-xx-xx", stop: str = "2020-xx-xx"):
    """
    指定された区間のrateデータを取得します。\n
    最大参照日数は366日です。\n
    返り値は辞書です。
    """
   return await items.get_rate_from_fullname_during_the_period("fullname", fullname, start, stop)


@app.get("/get_all_fullname", tags=["fullname api"])
async def get_all_fullname(_range: int = 10, _page: int = 1):
    """
    利用可能なキーをページを指定して取得します。\n
    返り値はリストです。
    """
    global all_fullname
    if all_fullname:
        pass
    else:
        all_fullname = await get_all_fullname_from_db()

    return make_page(all_fullname, _range, _page)

# id

# タグ検索


@app.post("/get_id_from_latest_tag_fuzzy_search", tags=["id api"])
async def get_id_from_latest_tag_fuzzy_search(tags: list = []):
    """
    tagからあいまい検索を行います。少なくとも1つは完全なtagが必要です。\n
    返り値はリストです。\n
    ng ["殿堂","爬虫"]\n
    ok ["殿堂","爬虫類"]\n
    """
    if len(tags) == 0:
        return []
    if tags[0] is None:
        return []
    cursor = search_tag_collection.find(
        {
            "$text": {"$search": " ".join(["\"" + str(i) + "\"" for i in tags])}
        },
        {
            "_id": 0,
            "id": 1
        }
    ).sort("id")
    result = [doc["id"] async for doc in cursor if "id" in doc]
    return result

# タグ検索


@app.post("/get_id_from_latest_tag_perfect_matching", tags=["id api"])
async def get_id_from_latest_tag_perfect_matching(tags: list = []):
    """
    tagから完全一致検索を行います。tagの要素は完全である必要があります。\n
    返り値はリストです。\n
    ng ["殿堂","爬虫類"]\n
    ok ["殿堂入り","爬虫類"]\n
    """
    if len(tags) == 0:
        return []
    if tags[0] is None:
        return []
    cursor = search_tag_collection.find(
        {
            "tags": {"$all": tags}
        },
        {
            "_id": 0,
            "id": 1,
        }
    ).sort("id")
    result = [doc["id"] async for doc in cursor if "id" in doc]
    return result

# 日時取得


@app.get("/get_dates_from_id", tags=["id api"])
async def get_dates_from_id(_id: str = "19439882", _range: int = 7, _page: int = 1):
    """
    取得可能なデータ日時をページ単位で取得します。\n
    返り値はリストです。
    """
    dates = await get_date_from_id_db(_id)
    return make_page(dates, _range, _page)


# 最新データ取得
@app.get("/get_latest_data_from_id", tags=["id api"])
async def get_latest_data_from_id(_id: str = "19439882"):
    """
    最新のデータを取得します。\n
    返り値は辞書です。該当がなければnullです。
    """
    return await search_tag_collection.find_one({"id": _id}, {"_id": 0})


# データ取得
@app.get("/get_data_from_id_and_date", tags=["id api"])
async def get_data_from_id_and_date(_id: str = "19439882", date: str = "2020-xx-xx"):
    """
    指定された日付のデータを取得します。\n
    返り値は辞書です。該当がなければnullです。
    """
    try:
        normalization_date = datetime.datetime.strptime(date, '%Y-%m-%d')
        normalization_date = str(
            datetime.date(
                normalization_date.year,
                normalization_date.month,
                normalization_date.day))
    except BaseException:
        normalization_date = date

    return await get_data_from_id_and_date_db(_id, normalization_date)

# rateデータ取得


@app.get("/get_rate_from_id_during_the_period", tags=["id api"])
async def get_rate_from_id_during_the_period(_id: str = "19439882", start: str = "2020-xx-xx", stop: str = "2020-xx-xx"):
    """
    指定された区間のrateデータを取得します。\n
    最大参照日数は366日です。\n
    返り値は辞書です。
    """
    max_dates = 367
    try:
        startdatetime = datetime.datetime.strptime(start, '%Y-%m-%d')
        stopdatetime = datetime.datetime.strptime(stop, '%Y-%m-%d')
    except BaseException:
        return {}
    startdate = datetime.date(
        startdatetime.year,
        startdatetime.month,
        startdatetime.day)
    stopdate = datetime.date(
        stopdatetime.year,
        stopdatetime.month,
        stopdatetime.day)
    date_range = int((stopdate - startdate).days)
    temp = []
    if max_dates < date_range:
        temp = [str(stopdate - datetime.timedelta(days=i))
                for i in range(max_dates)]
    else:
        temp = [str(stopdate - datetime.timedelta(days=i))
                for i in range(date_range)]
    if len(temp) == 0:
        return {}
    query = {"$or": [{"id": _id, "date": date} for date in temp]}

    cursor = data_collection.find(query, {
        "_id": 0, "date": 1, "rating": 1, "rating_votes": 1}).sort("date", -1)
    result = {doc["date"]: {key: doc[key] for key in doc.keys() if (key != "date")} async for doc in cursor}

    return result


@app.get("/get_all_id", tags=["id api"])
async def get_all_id(_range: int = 10, _page: int = 1):
    """
    利用可能なキーをページを指定して取得します。\n
    返り値はリストです。
    """
    global all_id
    if all_id:
        pass
    else:
        all_id = await get_all_id_from_db()
    return make_page(all_id, _range, _page)


@app.get("/", response_class=HTMLResponse)
async def read_root():
    html = """
    <!doctype html>
    <html lang="ja">
    <head>
        <!-- Required meta tags -->
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">

        <!-- Bootstrap CSS -->
        <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css" integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T" crossorigin="anonymous">

        <title>ayame api</title>
    </head>
    <body>
        <h1>Welcome to ayame api</h1>
        <a href=/docs target="_blank" rel="noopener noreferrer">document page here</a>
        <h2>How to use</h2>
        <ol>
            <li>You can get the fullname using <a href=/get_all_fullname target="_blank" rel="noopener noreferrer">/get_all_fullname</a>.</li>
            <li>Post the fullname with <a href=get_fullname_date target="_blank" rel="noopener noreferrer">/get_fullname_date</a> to get the available dates.</li>
            <li>Post the fullname and date to <a href=get_fullname_data target="_blank" rel="noopener noreferrer">/get_fullname_data</a> to get the metadata.</li>

        </ol>


        <!-- Optional JavaScript -->
        <!-- jQuery first, then Popper.js, then Bootstrap JS -->
        <script src="https://code.jquery.com/jquery-3.3.1.slim.min.js" integrity="sha384-q8i/X+965DzO0rT7abK41JStQIAqVgRVzpbzo5smXKp4YfRvH+8abtTE1Pi6jizo" crossorigin="anonymous"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.7/umd/popper.min.js" integrity="sha384-UO2eT0CpHqdSJQ6hJty5KVphtPhzWj9WO1clHTMGa3JDZwrnQq4sF86dIHNDz0W1" crossorigin="anonymous"></script>
        <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.min.js" integrity="sha384-JjSmVgyd0p3pXB1rRibZUAYoIIy6OrQ6VrjIEaFf/nJGzIxFDsf4x0xIM+B07jRM" crossorigin="anonymous"></script>
    </body>
    </html>

    """
    return html
