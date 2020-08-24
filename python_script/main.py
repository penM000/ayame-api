from fastapi import FastAPI
import motor.motor_asyncio

#データベースインスタンス作成
client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://mongodb:27017')
db = client['test_database']
collection = db["test_collection"]
app = FastAPI()



@app.get("/test")
async def test():
    document = {'key': 'value'}
    result = await db.test_collection.insert_one(document)
    return str(result)

@app.get("/")
def read_root():
    return {"Hello": "World"}
