import asyncio
import datetime
import json
import random
import string
import copy

import aiofiles
import motor.motor_asyncio

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
db = client['ayame_api']
collection = db["data_collection"]
data_collection = db["data_collection"]
search_tag_collection = db["tag_search"]
update_date_collection = db["last_update_date"]


JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')


# システム状態変数
update_status = "NO"
last_update = ""
all_mainkey = {}


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


async def make_index():
    await data_collection.create_index("id")
    await data_collection.create_index("fullname")
    await data_collection.create_index("date")
    await data_collection.create_index([("date", -1)])

    await search_tag_collection.create_index("id")
    await search_tag_collection.create_index("fullname")
    await search_tag_collection.create_index([("tags", 1)])
    await search_tag_collection.create_index([("tags", "text")])


async def update_data_db(newdocument, mainkey="id"):
    # 時刻インスタンス生成
    dt_now = datetime.datetime.now(JST)
    # 最新データとの比較
    # 日付のリストを取得
    dates = get_date_from_mainkey_db(mainkey, newdocument[mainkey])
    old_document = None
    if len(dates) == 0:
        pass
    else:
        old_document = await data_collection.find_one(
            {
                mainkey: newdocument[mainkey],
                "date": dates[0]
            },
            {
                "_id": 0
            }
        )
    if old_document is None:
        pass
    elif same_dictionary_check(newdocument, old_document, ["_id", "date"]):
        return

    document = await data_collection.find_one(
        {
            mainkey: newdocument[mainkey],
            "date": str(dt_now.date())
        }
    )
    # 新規登録データ
    if document is None:
        result = await data_collection.insert_one(newdocument)
    # 更新データ(同じ日付の更新)
    else:
        # データベースID取得
        _id = document['_id']
        # データベース更新
        result = await data_collection.replace_one({'_id': _id}, newdocument)
    return result

# tag検索用コレクション更新


async def update_tag_text_search_db(newdocument, mainkey="id"):
    document = await search_tag_collection.find_one(
        {mainkey: newdocument[mainkey]}
    )
    # 新規登録データ
    if document is None:
        result = await search_tag_collection.insert_one(newdocument)
    # 更新データ(同じ日付の更新)
    else:
        # データベースID取得
        _id = document['_id']
        # データベース更新
        result = await search_tag_collection.replace_one(
            {'_id': _id},
            newdocument
        )
    return result

# データベース最終更新日更新


async def update_last_update_date():
    dt_now = datetime.datetime.now(JST)
    document = await update_date_collection.find_one(
        {"last_update": "last_update"}
    )
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

        result = await update_date_collection.replace_one(
            {'_id': _id}, newdocument
        )
    return result

# データベース最終更新日取得


async def get_last_update_date():
    result = await update_date_collection.find_one(
        {"last_update": "last_update"},
        {"_id": 0, "fulldate": 1, "date": 1}
    )
    return result

# データベース最適化


async def compact_db():
    await db.command({"compact": "test_collection"})
    await db.command({"compact": "last_update_date"})
    await db.command({"compact": "tag_search"})


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


async def update():
    # 状態変数
    global update_status
    global all_mainkey
    update_status = "NO"

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
        async with aiofiles.open(
            '/update/ayame/data/data.json',
            mode='r'
        ) as f:
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

        # data db更新
        await update_data_db(copy.copy(newdocument))

        # tag検索用db更新
        await update_tag_text_search_db(copy.copy(newdocument))

    update_status = "NO"
    # データベース最適化
    await compact_db()

    # mainkey一覧更新
    all_mainkey["fullname"] = await get_all_mainkey_from_db("fullname")
    all_mainkey["id"] = await get_all_mainkey_from_db("id")
    # データベース更新日更新
    await update_last_update_date()
    return "update complete"


async def get_all_mainkey_from_db(mainkey):
    pipeline = [
        {
            "$group": {"_id": "$" + mainkey}
        },
        {
            "$sort": {"_id": 1}
        }
    ]
    cursor = data_collection.aggregate(pipeline, allowDiskUse=True)
    result = [doc["_id"] async for doc in cursor]
    return result


async def get_date_from_mainkey_db(mainkey, key):
    cursor = data_collection.find({mainkey: key}, {
        "_id": 0, "date": 1}).sort("date", -1)
    result = [doc["date"] async for doc in cursor]
    return result

# fullnameと日付で全情報を取得


async def get_data_from_mainkey_and_date_db(mainkey, key, date):
    document = await data_collection.find_one(
        {
            mainkey: key,
            "date": date
        },
        {
            "_id": 0
        }
    )
    return document


async def get_mainkey_from_latest_tag_fuzzy_search(mainkey, tags):
    if len(tags) == 0:
        return []
    if tags[0] is None:
        return []
    cursor = search_tag_collection.find(
        {
            "$text": {
                "$search": " ".join(["\"" + str(i) + "\"" for i in tags])
            }
        },
        {
            "_id": 0,
            mainkey: 1
        }
    ).sort(mainkey)
    result = [
        doc[mainkey] async for doc in cursor
        if mainkey in doc and doc[mainkey] is not None
    ]
    return result


async def get_mainkey_from_latest_tag_perfect_matching(mainkey, tags):

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
            mainkey: 1,
            "date": 1
        }
    ).sort(mainkey)
    result = [
        doc[mainkey] async for doc in cursor
        if mainkey in doc and doc[mainkey] is not None
    ]
    return result


async def get_status():
    global all_fullname
    global all_id
    dt_now = datetime.datetime.now(JST)
    if len(all_fullname) == 0:
        all_fullname = await get_all_mainkey_from_db("fullname")
    fulldate = await get_last_update_date()
    status = {
        "update_status": update_status,
        "date": dt_now.date(),
        "total_fullname": len(all_fullname),
        "last_update": fulldate["fulldate"]}
    return status


async def get_data_from_mainkey_and_date(mainkey, key, date):

    try:
        normalization_date = datetime.datetime.strptime(date, '%Y-%m-%d')
        normalization_date = str(
            datetime.date(
                normalization_date.year,
                normalization_date.month,
                normalization_date.day))
    except BaseException:
        normalization_date = date
    result = get_data_from_mainkey_and_date_db(
        mainkey,
        key,
        normalization_date
    )
    return await result


async def get_rate_from_mainkey_during_the_period(mainkey, key, start, stop):
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

    query = {"$or": [{mainkey: key, "date": date} for date in temp]}

    cursor = data_collection.find(query, {
        "_id": 0, "date": 1, "rating": 1, "rating_votes": 1}).sort("date", -1)
    result = {
        doc["date"]: {key: doc[key] for key in doc.keys()
                      if (key != "date")} async for doc in cursor
    }
    return result


async def get_all_mainkey(mainkey, _range, _page):
    global all_mainkey
    if mainkey in all_mainkey:
        pass
    else:
        all_mainkey[mainkey] = await get_all_mainkey_from_db(mainkey)
    return make_page(all_mainkey[mainkey], _range, _page)


async def get_dates_from_mainkey(mainkey, key, _range, _page):
    dates = await get_date_from_mainkey_db(mainkey, key)
    return make_page(dates, _range, _page)
