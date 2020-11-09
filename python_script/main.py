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
#from fastapi.middleware.gzip import GZipMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import HTMLResponse
from pydantic import BaseModel



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


# データベースインスタンス作成
client = motor.motor_asyncio.AsyncIOMotorClient(
    'mongodb://mongodb:27017/?compressors=snappy')
db = client['test_database']
collection = db["test_collection"]
data_collection = db["test_collection"]
search_tag_collection = db["tag_search"]
update_date_collection = db["last_update_date"]

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

# 非同期コマンド実行


async def run(cmd, cwd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    print(f'[{cmd!r} exited with {proc.returncode}]')
    if stdout:
        print(f'[stdout]\n{stdout.decode()}')
    if stderr:
        print(f'[stderr]\n{stderr.decode()}')

# ページ切り出し


def make_page(_list, _range, _page):
    _min = abs(_range) * (abs(_page) - 1)
    _max = abs(_range) * (abs(_page))
    if _min < 0:
        _min = 0
    if _max > len(_list):
        _max = len(_list)
    return _list[_min: _max]

# 辞書の比較


def same_dictionary_check(dict1, dict2, exclusion_key_list=["date"]):
    """
    辞書が同じならTrue
    """
    # 辞書の独立化
    copy_dict1, copy_dict2 = copy.copy(dict1), copy.copy(dict2)
    for exclusion_key in exclusion_key_list:
        try:
            del copy_dict1[exclusion_key]
        except KeyError:
            pass

        try:
            del copy_dict2[exclusion_key]
        except KeyError:
            pass
    if copy_dict1 == copy_dict2:
        return True
    else:
        return False

# db関連
# dbインデックス作成


async def make_index():
    await data_collection.create_index("id")
    await data_collection.create_index("fullname")
    await data_collection.create_index("date")
    await data_collection.create_index([("date", -1)])
    # await data_collection.create_index([ ("tags", "text")])
    # await data_collection.create_index([ ("tags", 1)])
    await search_tag_collection.create_index("id")
    await search_tag_collection.create_index("fullname")
    await search_tag_collection.create_index([("tags", 1)])
    await search_tag_collection.create_index([("tags", "text")])

# fullnameの取得


async def get_all_fullname_from_db():
    pipeline = [
        {
            "$group": {"_id": "$fullname"}
        },
        {
            "$sort": {"_id": 1}
        }
    ]
    cursor = data_collection.aggregate(pipeline, allowDiskUse=True)
    return [doc["_id"] async for doc in cursor]

# fullnameで登録されている日付を取得


async def get_date_from_fullname_db(fullname):
    cursor = data_collection.find({'fullname': fullname}, {
        "_id": 0, "date": 1}).sort("date", -1)
    result = [doc["date"] async for doc in cursor]
    return result

# fullnameと日付で全情報を取得


async def get_data_from_fullname_and_date_db(fullname, date):
    document = await data_collection.find_one(
        {
            "fullname": fullname,
            "date": date
        },
        {
            "_id": 0
        }
    )
    return document

# idの取得


async def get_all_id_from_db():
    pipeline = [
        {
            "$group": {"_id": "$id"}
        },
        {
            "$sort": {"_id": 1}
        }
    ]
    cursor = data_collection.aggregate(pipeline, allowDiskUse=True)
    return [doc["_id"] async for doc in cursor if doc["_id"] is not None]

# idで登録されている日付を取得


async def get_date_from_id_db(_id):
    cursor = data_collection.find({'id': _id}, {
        "_id": 0, "date": 1}).sort("date", -1)
    result = [doc["date"] async for doc in cursor]
    return result

# idと日付で全情報を取得


async def get_data_from_id_and_date_db(_id, date):
    document = await data_collection.find_one(
        {
            "id": _id,
            "date": date
        },
        {
            "_id": 0
        }
    )
    return document

# データベース更新


async def update_data_db(newdocument, mainkey="id"):
    # 時刻インスタンス生成
    dt_now = datetime.datetime.now(JST)
    # 最新データとの比較
    # 日付のリストを取得
    dates = await get_date_from_id_db(newdocument[mainkey])
    old_document = None
    if len(dates) == 0:
        pass
    else:
        old_document = await data_collection.find_one({mainkey: newdocument[mainkey], "date": dates[0]}, {"_id": 0})

    # old_document = await search_tag_collection.find_one({mainkey:
    # newdocument[mainkey]},{"_id":0})
    if old_document is None:
        pass
    elif same_dictionary_check(newdocument, old_document, ["_id", "date"]):
        return

    document = await data_collection.find_one({mainkey: newdocument[mainkey], "date": str(dt_now.date())})
    # 新規登録データ
    if document is None:
        result = await data_collection.insert_one(newdocument)
    # 更新データ(同じ日付の更新)
    else:
        # データベースID取得
        _id = document['_id']
        # データベース更新
        result = await data_collection.replace_one({'_id': _id}, newdocument)
    return

# tag検索用コレクション更新


async def update_tag_text_search_db(newdocument, mainkey="id"):
    document = await search_tag_collection.find_one({mainkey: newdocument[mainkey]})
    # 新規登録データ
    if document is None:
        result = await search_tag_collection.insert_one(newdocument)
    # 更新データ(同じ日付の更新)
    else:
        # データベースID取得
        _id = document['_id']
        # データベース更新
        result = await search_tag_collection.replace_one({'_id': _id}, newdocument)
    return

# データベース最終更新日更新


async def update_last_update_date():
    dt_now = datetime.datetime.now(JST)
    document = await update_date_collection.find_one({"last_update": "last_update"})
    newdocument = {
        "last_update": "last_update",
        "fulldate": str(dt_now),
        "date": str(dt_now.date())
    }
    if document is None:
        result = await update_date_collection.insert_one(newdocument)
    # 更新データ(同じ日付の更新)
    else:
        # データベースID取得
        _id = document['_id']
        # データベース更新

        result = await update_date_collection.replace_one({'_id': _id}, newdocument)
    return result

# データベース最終更新日取得


async def get_last_update_date():
    result = await update_date_collection.find_one({"last_update": "last_update"}, {"_id": 0, "fulldate": 1, "date": 1})
    return result

# データベース最適化


async def compact_db():
    await db.command({"compact": "test_collection"})
    await db.command({"compact": "last_update_date"})
    await db.command({"compact": "tag_search"})


def change_structure(dict1):
    try:
        temp = {}
        dict1_copy = copy.copy(dict1)
        temp.update(dict1_copy)
        temp.update(dict1_copy["data"])
        del temp["data"]
        return temp
    except BaseException:
        return False


# データベース構造変更用
"""
@app.get("/test")
async def test():
    cursor = data_collection.find({})
    async for doc in cursor:
        temp=change_structure(doc)
        if False == temp:
            pass
        else:
            result = await data_collection.replace_one({'_id': temp["_id"]}, temp)
    return
"""
# 状態取得


@app.get("/status")
async def get_status():
    global all_fullname
    global all_id
    dt_now = datetime.datetime.now(JST)
    if len(all_fullname) == 0:
        all_fullname = await get_all_fullname_from_db()
    fulldate = await get_last_update_date()
    status = {
        "update_status": update_status,
        "date": dt_now.date(),
        "total_fullname": len(all_fullname),
        "last_update": fulldate["fulldate"]}
    return status

# データベース更新


@app.get("/update", tags=["update"])
async def update(password: str = ""):
    # 状態変数
    global update_status
    global all_fullname
    update_status = "NO"
    # パスワード認証(手抜き)
    if password == update_password:
        pass
    else:
        return "progress"
    # アップデート処理中なら終了
    if update_status == "NO":
        update_status = "progress"
    else:
        return update_status

    # クローラ非同期マルチプロセス実行
    try:
        update_status = "get data"
        await run("python3 /update/ayame/src/get_all.py", "/update/ayame")
    except BaseException:
        update_status = "NO"
        return "being24 error"

    # クロールデータのメモリロード
    try:
        json_contents = ""
        async with aiofiles.open('/update/ayame/data/data.json', mode='r') as f:
            json_contents = await f.read()
        json_load = json.loads(str(json_contents))
    except BaseException:
        update_status = "NO"
        return "file load error"

    # データベース更新
    # try:
    # データベースインデックス作成
    await make_index()

    # 進捗状況用変数
    total = len(json_load)
    now_count = 0

    # 時刻インスタンス生成
    dt_now = datetime.datetime.now(JST)

    for idata in json_load:

        # 進捗状況更新
        now_count += 1
        update_status = str(now_count) + "/" + str(total) + \
            " : " + str(round((now_count / total) * 100, 2)) + "%"
        # データ構造の自動生成

        newdocument = {key: idata[key]
                       for key in idata.keys() if (key != "tags")}
        newdocument["tags"] = idata["tags"].split(" ")
        newdocument["date"] = str(dt_now.date())
        """
        newdocument = {
            "id"        :   idata["id"],
            "fullname"  :   idata["fullname"],
            "date"      :   str( dt_now.date() ),
            "tags"      :   idata["tags"].split(" ") ,
            "data"      :   {key: idata[key] for key in idata.keys() if ( key != "fullname" ) and ( key != "tags" ) and ( key != "id" )}
        }
        """

        # data db更新
        await update_data_db(copy.copy(newdocument))

        # tag検索用db更新
        await update_tag_text_search_db(copy.copy(newdocument))

    update_status = "NO"
    # データベース最適化
    await compact_db()

    # fullname一覧更新
    all_fullname = await get_all_fullname_from_db()
    all_id = await get_all_id_from_db()

    # データベース更新日更新
    await update_last_update_date()

    return "update complete"
    # except BaseException:
    #    update_status = "NO"
    #    return "update error"

# fullname
# タグ検索


@app.post("/get_fullname_from_latest_tag_fuzzy_search", tags=["fullname api"])
async def get_fullname_from_latest_tag(tags: list = []):
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
            "fullname": 1
        }
    ).sort("fullname")
    result = [doc["fullname"] async for doc in cursor if "fullname" in doc and doc["fullname"] is not None]
    return result

# タグ検索


@app.post("/get_fullname_from_latest_tag_perfect_matching",
          tags=["fullname api"])
async def test_get_fullname_from_latest_tag(tags: list = []):
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
            "fullname": 1,
            "date": 1
        }
    ).sort("fullname")
    result = [doc["fullname"] async for doc in cursor if "fullname" in doc and doc["fullname"] is not None]
    return result

# 日時取得


@app.get("/get_dates_from_fullname", tags=["fullname api"])
async def get_dates_from_fullname(fullname: str = "scp-173", _range: int = 7, _page: int = 1):
    """
    取得可能なデータ日時をページ単位で取得します。\n
    返り値はリストです。
    """
    dates = await get_date_from_fullname_db(fullname)
    return make_page(dates, _range, _page)

# 最新データ取得


@app.get("/get_latest_data_from_fullname", tags=["fullname api"])
async def get_latest_data_from_fullname(fullname: str = "scp-173"):
    """
    最新のデータを取得します。\n
    返り値は辞書です。
    """
    return await search_tag_collection.find_one({"fullname": fullname}, {"_id": 0})


# データ取得
@app.get("/get_data_from_fullname_and_date", tags=["fullname api"])
async def get_data_from_fullname_and_date(fullname: str = "scp-173", date: str = "2020-xx-xx"):
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
    return await get_data_from_fullname_and_date_db(fullname, normalization_date)

# rateデータ取得


@app.get("/get_rate_from_fullname_during_the_period", tags=["fullname api"])
async def get_rate_from_fullname_during_the_period(fullname: str = "scp-173", start: str = "2020-xx-xx", stop: str = "2020-xx-xx"):
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

    query = {"$or": [{"fullname": fullname, "date": date} for date in temp]}

    cursor = data_collection.find(query, {
        "_id": 0, "date": 1, "rating": 1, "rating_votes": 1}).sort("date", -1)
    result = {doc["date"]: {key: doc[key] for key in doc.keys() if (key != "date")} async for doc in cursor}
    return result


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
