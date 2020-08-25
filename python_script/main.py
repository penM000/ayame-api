from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel
import motor.motor_asyncio
import datetime
import json
import aiofiles
import asyncio


#アップデートパスワード
update_password="hello world"

#データベースインスタンス作成
client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://mongodb:27017/?compressors=snappy')
db = client['test_database']
collection = db["test_collection"]

#fastapiインスタンス作成
app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=500)

#タイムゾーン設定
JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')

#システム状態変数
update_status="NO"

# リクエストbodyを定義
class request_data(BaseModel):
    fullname: str
    date: str
class request_date(BaseModel):
    fullname: str
class updatepass(BaseModel):
    password: str

#非同期コマンド実行
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


#状態取得
@app.get("/status")
async def get_status():
    dt_now=datetime.datetime.now(JST)
    status={"update_status":update_status,"date":dt_now.date(),"fulldate":dt_now}
    return status
#データベースアップデート
@app.post("/update")
async def update(update:updatepass):
    #状態変数
    global update_status
    #パスワード認証(手抜き)
    if update.password==update_password:
        pass
    else:
        return "progress"
    #アップデート処理中なら終了
    if update_status=="NO":
        update_status="progress"
    else:
        return update_status
    #時刻インスタンス生成
    dt_now=datetime.datetime.now(JST)
    #クローラ非同期マルチプロセス実行
    
    try:
        update_status="get data"
        await run("python3 /update/being24/get_all.py")
    except:
        update_status="NO"
        return "being24 error"
    
    #クロールデータのメモリロード
    try:
        json_contents=""
        async with aiofiles.open('/update/being24/data/data.json', mode='r') as f:
            json_contents = await f.read()
        json_load = json.loads(str(json_contents))
    except:
        update_status="NO"
        return "file load error"
    #データベース更新
    try:
    #データベースインデックス作成
        await collection.create_index("fullname")
        await collection.create_index("date")
        #進捗状況用変数
        total=len(json_load)
        now_count=0
        for idata in json_load:
            now_count+=1
            #進捗状況更新
            update_status=str(now_count) + "/" + str(total) + " : " + str( round( (now_count/total)*100 ,2 )) + "%"
            document = await collection.find_one({"fullname": idata["fullname"],"date":str(dt_now.date())})
            #データ構造の自動生成
            newdocument={
                "fullname": idata["fullname"],
                "date":str( dt_now.date() ),
                "data":{key:idata[key] for key in idata.keys() if key !="fullname"}
            }
            #新規登録データ
            if document is None:
                result = await collection.insert_one(newdocument)
            #更新データ(同じ日付の更新)
            else:
                #データベースID取得
                _id = document['_id']
                #データベース更新
                result = await collection.replace_one({'_id': _id}, newdocument)
        update_status="NO"
        await db.command({ "compact": "test_collection"})
        return "ok"
    except:
        update_status="NO"
        return "update error"


#日時取得
@app.post("/get_fullname_date")
async def get_fullname_date(get_fullname_date:request_date):
    cursor =  collection.find({'fullname': get_fullname_date.fullname},{"_id":0,"date":1}).sort("date",-1)
    result=[doc["date"]  async for doc in cursor ]
    return result



#データ取得      
@app.post("/get_fullname_data")
async def get_fullname_data(get_fullname_data:request_data):
    document =  await collection.find_one(
        {
            'fullname': get_fullname_data.fullname,
            "date":get_fullname_data.date
        },
        {
            "_id":0,
            "fullname":1,
            "date":1,
            "data":1
        }
    )
    return document

@app.get("/get_all_fullname")
async def get_all_fullname():
    pipeline = [

        {
            "$group": {"_id":"$fullname"}
        },
        {
            "$sort": { "_id": 1 }
        }
    ]
    cursor = collection.aggregate(pipeline)
    result=[doc["_id"] async for doc in cursor]
    return result
    



@app.get("/")
async def read_root():
    return "ok"
