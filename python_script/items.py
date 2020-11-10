import asyncio
import datetime
import json
import random
import string
import copy

import aiofiles

import database

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


# システム状態変数
update_status = "NO"
last_update = ""
all_mainkey = {}


# データベース最適化


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
    await database.make_index()

    # 進捗状況用変数
    total = len(json_load)
    now_count = 0

    # 時刻インスタンス生成
    JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
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
        newdocument = database.convert_str_in_a_document_to_datetime(
            newdocument)

        # data db更新
        await database.update_data_db(copy.copy(newdocument))

        # tag検索用db更新
        await database.update_tag_text_search_db(copy.copy(newdocument))

        await database.update_metatitle_text_search_db(copy.copy(newdocument))

    update_status = "NO"
    # データベース最適化
    await database.compact_db()

    # mainkey一覧更新
    all_mainkey["fullname"] = await database.get_all_mainkey_from_db(
        "fullname"
    )
    all_mainkey["id"] = await database.get_all_mainkey_from_db("id")
    # データベース更新日更新
    await database.update_last_update_date()
    return "update complete"


# fullnameと日付で全情報を取得


async def get_metatitle_search(metatitle):
    result = await database.metatitle_search(metatitle)
    return result


async def get_mainkey_from_latest_tag_fuzzy_search(mainkey, tags):
    if len(tags) == 0:
        return []
    if tags[0] is None:
        return []
    cursor = database.search_tag_collection.find(
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
    cursor = database.search_tag_collection.find(
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
    global all_mainkey
    JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
    dt_now = datetime.datetime.now(JST)
    if "fullname" not in all_mainkey:
        all_mainkey["fullname"] = await database.get_all_mainkey_from_db(
            "fullname"
        )
    fulldate = await database.get_last_update_date()
    status = {
        "update_status": update_status,
        "date": dt_now.date(),
        "total_fullname": len(all_mainkey["fullname"]),
        "last_update": fulldate}
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
    result = database.get_data_from_mainkey_and_date_db(
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

    cursor = database.data_collection.find(query, {
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
        all_mainkey[mainkey] = await database.get_all_mainkey_from_db(mainkey)
    return make_page(all_mainkey[mainkey], _range, _page)


async def get_dates_from_mainkey(mainkey, key, _range, _page):
    dates = await database.get_date_from_mainkey_db(mainkey, key)
    return make_page(dates, _range, _page)


async def get_id_from_metatitle(metatitle):
    result = await database.get_id_from_metatitle(metatitle)
    return result


async def get_id_during_time_from_created_at(start, stop):
    result = await database.get_id_during_time_from_created_at(start, stop)
    return result


async def get_latest_data_from_mainkey(mainkey,key):
    return await database.search_tag_collection.find_one(
        {mainkey: key},
        {"_id": 0}
    )
