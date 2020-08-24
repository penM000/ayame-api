from fastapi import FastAPI
import motor.motor_asyncio
import datetime
import json
import aiofiles
import asyncio

from pydantic import BaseModel
#アップデートパスワード
update_password="hello world"

#データベースインスタンス作成
client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://mongodb:27017')
db = client['test_database']
collection = db["test_collection"]
app = FastAPI()

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



@app.get("/status")
async def get_status():
    dt_now=datetime.datetime.now(JST)
    status={"update_status":update_status,"date":dt_now.date(),"fulldate":dt_now}
    return status




@app.post("/update")
async def update(update:updatepass):
    if update.password==update_password:
        pass
    else:
        return "progress"

    global update_status
    if update_status=="NO":
        pass
    else:
        return update_status

    update_status="progress"


    dt_now=datetime.datetime.now(JST)
    json_contents=""
   
    try:

        update_status="get data"
        await run("python3 /update/being24/get_all.py")
    except:
        update_status="NO"
        return "being24 error"
   
    try:
        async with aiofiles.open('/update/being24/data/data.json', mode='r') as f:
            json_contents = await f.read()
        json_load = json.loads(str(json_contents))
    except:
        update_status="get data"
        return "file error"

    try:
        total=len(json_load)
        now_count=0
        for idata in json_load:
            now_count+=1
            update_status=str(now_count) + "/" + str(total) + " : " + str( round( (now_count/total)*100 ,2 )) + "%"
            document = await collection.find_one({'fullname': idata["fullname"]})
            #データ構造テンプレ
            newdocument =   {
                            "fullname": idata["fullname"],
                            str(dt_now.date()):{
                            #str("2020-08-25"):{
                                "title": idata["title"],
                                "tags": idata["tags"],
                                "comments": idata["comments"],
                                "rating": idata["rating"],
                                "rating_votes": idata["rating_votes"],
                                "created_at": idata["created_at"],
                                "created_by": idata["created_by"],
                                "updated_at": idata["updated_at"],
                                "updated_by": idata["updated_by"],
                                "commented_at": idata["commented_at"],
                                "commented_by": idata["commented_by"]   
                            }   
                        }
            #新規登録データ
            if document is None:
                result = await collection.insert_one(newdocument)
            #更新データ
            else:
                #データベースID取得
                _id = document['_id']
                #データベースの情報と更新データの結合
                for datekey in document.keys():
                    if str(datekey) != "_id" and str(datekey) != "fullname" :  
                        newdocument.update({str(datekey):document[datekey]})
                        pass
                #データベース更新
                result = await collection.replace_one({'_id': _id}, newdocument)
        update_status="NO"
        return "ok"
    except:
        update_status="NO"
        return "update error"

#日時取得
@app.post("/get_fullname_date")
async def get_fullname_date(get_fullname_date:request_date):
    document = await collection.find_one({'fullname': get_fullname_date.fullname})
    if document is None:
        return "not found"
    else:
        dates=[]
        for datekey in document.keys():
            if str(datekey) != "_id" and str(datekey) != "fullname" : 
                dates.append(datekey) 
        return dates
#データ取得      
@app.post("/get_fullname_data")
async def get_fullname_data(get_fullname_data:request_data):
    document = await collection.find_one({'fullname': get_fullname_data.fullname})
    if document is None:
        return "not found"
    else:
        dates=[]
        for datekey in document.keys():
            if str(datekey) == get_fullname_data.date: 
                return document[datekey]
        return "not found"


@app.get("/")
def read_root():
    return {"Hello": "World"}
