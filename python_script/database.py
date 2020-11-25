import motor.motor_asyncio
import datetime
import copy
import dateutil.parser
# データベースインスタンス作成
database_name = "ayame_api"
data_collection_name = "data_collection"
search_tag_collection_name = "tag_search"
update_date_collection_name = "last_update_date"

client = motor.motor_asyncio.AsyncIOMotorClient(
    'mongodb://mongodb:27017/?compressors=snappy')
db = client[database_name]
collection = db[data_collection_name]
data_collection = db[data_collection_name]
search_tag_collection = db[search_tag_collection_name]

update_date_collection = db[update_date_collection_name]


async def make_index():
    await data_collection.create_index("id")
    await data_collection.create_index("fullname")
    await data_collection.create_index("date")
    await data_collection.create_index([("date", -1)])

    await search_tag_collection.create_index("id")
    await search_tag_collection.create_index("fullname")
    await search_tag_collection.create_index("created_at")
    await search_tag_collection.create_index([("tags", 1)])
    await search_tag_collection.create_index([("metatitle", 1)])


async def compact_db():
    await db.command({"compact": data_collection_name})
    await db.command({"compact": search_tag_collection_name})
    await db.command({"compact": update_date_collection_name})


def convert_str_in_a_document_to_datetime(document):
    doc = copy.copy(document)
    try:
        doc["created_at"] = dateutil.parser.parse(str(doc["created_at"]))
    except BaseException:
        pass
    try:
        doc["updated_at"] = dateutil.parser.parse(str(doc["updated_at"]))
    except BaseException:
        pass
    try:
        doc["commented_at"] = dateutil.parser.parse(str(doc["commented_at"]))
    except BaseException:
        pass
    return doc


async def get_id_during_time_from_created_at(start, stop):
    try:
        start = datetime.datetime.strptime(start, '%Y-%m-%d')
        stop = datetime.datetime.strptime(stop, '%Y-%m-%d')
    except BaseException:
        return

    cursor = search_tag_collection.find(
        {"created_at": {'$lt': stop, '$gte': start}})
    result = [doc["id"] async for doc in cursor if doc["id"] is not None]
    return result


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


async def get_date_from_mainkey_db(mainkey, key):
    cursor = data_collection.find({mainkey: key}, {
        "_id": 0, "date": 1}).sort("date", -1)
    result = [doc["date"] async for doc in cursor]
    return result


async def update_data_db(newdocument, mainkey="id"):
    # 時刻インスタンス生成
    JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
    dt_now = datetime.datetime.now(JST)
    # 最新データとの比較
    # 日付のリストを取得
    dates = await get_date_from_mainkey_db(mainkey, newdocument[mainkey])
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
        result = await data_collection.replace_one(
            {'_id': _id},
            newdocument
        )
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
    JST = datetime.timezone(datetime.timedelta(hours=+9), 'JST')
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
    result = [doc["_id"] async for doc in cursor if doc["_id"] is not None]
    return result


async def metatitle_search(metatitle):
    cursor = search_tag_collection.find(
        {
            "metatitle": {"$regex": metatitle},
        },
        {
            "_id": 0,
            "metatitle": 1
        }
    ).sort("metatitle")
    result = [
        doc["metatitle"] async for doc in cursor
        if "metatitle" in doc and doc["metatitle"] is not None
    ]
    return result


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


async def get_id_from_metatitle(metatitle):
    document = await search_tag_collection.find_one(
        {
            "metatitle": metatitle,
        },
        {
            "_id": 0,
            "id": 1
        }
    )
    return document
