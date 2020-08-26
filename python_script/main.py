import asyncio
import datetime
import json
import random
import string

import aiofiles
import motor.motor_asyncio
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
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

# fastapiインスタンス作成
app = FastAPI()
#app.add_middleware(GZipMiddleware, minimum_size=500)

# タイムゾーン設定
JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')

# システム状態変数
update_status = "NO"

all_fullname=[]


# 非同期コマンド実行


async def run(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    print(f'[{cmd!r} exited with {proc.returncode}]')
    if stdout:
        print(f'[stdout]\n{stdout.decode()}')
    if stderr:
        print(f'[stderr]\n{stderr.decode()}')


# 状態取得
@app.get("/status")
async def get_status():
    dt_now = datetime.datetime.now(JST)
    status = {
        "update_status": update_status,
        "date": dt_now.date(),
        "fulldate": dt_now}
    return status
# データベースアップデート





@app.get("/update")
async def update(password: str = ""):
    # 状態変数
    global update_status
    global all_fullname
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
    # 時刻インスタンス生成
    dt_now = datetime.datetime.now(JST)
    # クローラ非同期マルチプロセス実行

    try:
        update_status = "get data"
        await run("python3 /update/being24/get_all.py")
    except BaseException:
        update_status = "NO"
        return "being24 error"

    # クロールデータのメモリロード
    try:
        json_contents = ""
        async with aiofiles.open('/update/being24/data/data.json', mode='r') as f:
            json_contents = await f.read()
        json_load = json.loads(str(json_contents))
    except BaseException:
        update_status = "NO"
        return "file load error"
    # データベース更新
    try:
        # データベースインデックス作成
        await collection.create_index("fullname")
        await collection.create_index("date")
        # 進捗状況用変数
        total = len(json_load)
        now_count = 0
        for idata in json_load:
            now_count += 1
            # 進捗状況更新
            update_status = str(now_count) + "/" + str(total) + \
                " : " + str(round((now_count / total) * 100, 2)) + "%"
            document = await collection.find_one({"fullname": idata["fullname"], "date": str(dt_now.date())})
            # データ構造の自動生成
            newdocument = {
                "fullname": idata["fullname"], "date": str(
                    dt_now.date()), "data": {
                    key: idata[key] for key in idata.keys() if key != "fullname"}}
            # 新規登録データ
            if document is None:
                result = await collection.insert_one(newdocument)
            # 更新データ(同じ日付の更新)
            else:
                # データベースID取得
                _id = document['_id']
                # データベース更新
                result = await collection.replace_one({'_id': _id}, newdocument)
        update_status = "NO"
        await db.command({"compact": "test_collection"})
        pipeline = [
            {
                "$group": {"_id": "$fullname"}
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        cursor = collection.aggregate(pipeline,allowDiskUse=True)
        all_fullname = [doc["_id"] async for doc in cursor]
        return "ok"
    except BaseException:
        update_status = "NO"
        return "update error"

# 日時取得
@app.get("/get_fullname_date")
async def get_fullname_date(fullname: str = "scp-173"):
    cursor = collection.find({'fullname': fullname}, {
                             "_id": 0, "date": 1}).sort("date", -1)
    result = [doc["date"] async for doc in cursor]
    return result


# データ取得
@app.get("/get_fullname_data")
async def get_fullname_data(fullname: str = "scp-173",date: str = "2020-xx-xx"):
    document = await collection.find_one(
        {
            'fullname': fullname,
            "date": date
        },
        {
            "_id": 0,
            "fullname": 1,
            "date": 1,
            "data": 1
        }
    )
    return document


@app.get("/get_all_fullname")
async def get_all_fullname(_range: int = 10, _page: int = 1):
    global all_fullname
    if all_fullname:
        pass
    else:
        pipeline = [
            {
                "$group": {"_id": "$fullname"}
            },
            {
                "$sort": {"_id": 1}
            }
        ]
        cursor = collection.aggregate(pipeline,allowDiskUse=True)
        all_fullname = [doc["_id"] async for doc in cursor]
    _min=_range*( _page - 1 )
    _max=_range*( _page  )
    if _min<0:
        _min=0
    if _max>len(all_fullname):
        _max=len(all_fullname)
    result=all_fullname[ _min : _max ]
    
    return result
##一番重い処理の最適化のためのexplain確認用
"""
@app.get("/test_get_all_fullname")
async def test_get_all_fullname():
    pipeline = [
        {
            "$group": {"_id": "$fullname"}
        },
        {
            "$sort": {"_id": 1}
        }
        
    ]
    result = await db.command('explain', {'aggregate': 'test_collection', 'pipeline': pipeline, 'cursor': {}}, verbosity='executionStats')
    #result = await db.command('aggregate', 'test_collection', pipeline=pipeline, explain=True)
    #cursor = collection.aggregate(pipeline,allowDiskUse=True)
    #result = [doc["_id"] async for doc in cursor]
    return result
"""

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
