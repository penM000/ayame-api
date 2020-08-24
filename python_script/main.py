from fastapi import FastAPI
import motor.motor_asyncio
import datetime

#データベースインスタンス作成
client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://mongodb:27017')
db = client['test_database']
collection = db["test_collection"]
app = FastAPI()

#タイムゾーン設定
JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')


#システム状態変数
update_status="NO"

@app.get("/status")
async def get_status():
    dt_now=datetime.datetime.now(JST)
    status={"update_status":update_status,"date":dt_now.date(),"fulldate":dt_now}
    return status


@app.get("/test")
async def test():
    document = {'key': 'value'}
    result = await db.test_collection.insert_one(document)
    return str(result)

@app.get("/")
def read_root():
    return {"Hello": "World"}
