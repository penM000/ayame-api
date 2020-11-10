from fastapi import FastAPI
# from fastapi.middleware.gzip import GZipMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import HTMLResponse
# from pydantic import BaseModel
import items


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
    },
    {
        "name": "metatitle api",
        "description": "metatitle 検索用 api",
    },
    {
        "name": "akanesasu api",
        "description": "茜刺財団新聞集計用api",
    }
]


# fastapiインスタンス作成
app = FastAPI(
    title="ayame api",
    description="This is a very fancy project, with auto\
        docs for the API and everything",
    version="1.0.0",
    openapi_tags=tags_metadata)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
# プロキシヘッダー読み取り
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")


# 状態取得
@app.get("/status")
async def get_status():
    return await items.get_status()

# 状態取得


@app.get("/update", tags=["update"])
async def update(password: str = ""):
    return await items.update()


@app.get("/get_metatitle_search", tags=["metatitle api"])
async def get_metatitle_search(metatitle: str):
    """

    """
    result = await items.get_metatitle_search(metatitle)
    return result


@app.get("/get_id_from_metatitle", tags=["metatitle api"])
async def get_id_from_metatitle(metatitle: str):
    """

    """
    result = await items.get_id_from_metatitle(metatitle)
    return result


@app.post("/get_fullname_from_latest_tag_fuzzy_search", tags=["fullname api"])
async def get_fullname_from_latest_tag_fuzzy_search(tags: list = []):
    """
    tagからあいまい検索を行います。少なくとも1つは完全なtagが必要です。\n
    返り値はリストです。\n
    ng ["殿堂","爬虫"]\n
    ok ["殿堂","爬虫類"]\n
    """
    return await items.get_mainkey_from_latest_tag_fuzzy_search("fullname",
                                                                tags)


@app.post("/get_id_from_latest_tag_fuzzy_search", tags=["id api"])
async def get_id_from_latest_tag_fuzzy_search(tags: list = []):
    """
    tagからあいまい検索を行います。少なくとも1つは完全なtagが必要です。\n
    返り値はリストです。\n
    ng ["殿堂","爬虫"]\n
    ok ["殿堂","爬虫類"]\n
    """
    return await items.get_mainkey_from_latest_tag_fuzzy_search("id", tags)


@app.post("/get_fullname_from_latest_tag_perfect_matching",
          tags=["fullname api"])
async def get_fullname_from_latest_tag_perfect_matching(tags: list = []):
    """
    tagから完全一致検索を行います。tagの要素は完全である必要があります。\n
    返り値はリストです。\n
    ng ["殿堂","爬虫類"]\n
    ok ["殿堂入り","爬虫類"]\n
    """
    return await items.get_mainkey_from_latest_tag_perfect_matching("fullname",
                                                                    tags)


@app.post("/get_id_from_latest_tag_perfect_matching", tags=["id api"])
async def get_id_from_latest_tag_perfect_matching(tags: list = []):
    """
    tagから完全一致検索を行います。tagの要素は完全である必要があります。\n
    返り値はリストです。\n
    ng ["殿堂","爬虫類"]\n
    ok ["殿堂入り","爬虫類"]\n
    """
    return await items.get_mainkey_from_latest_tag_perfect_matching("id", tags)


@app.get("/get_dates_from_fullname", tags=["fullname api"])
async def get_dates_from_fullname(
    fullname: str = "scp-173",
    _range: int = 7,
    _page: int = 1
):
    """
    取得可能なデータ日時をページ単位で取得します。\n
    返り値はリストです。
    """
    return await items.get_dates_from_mainkey(
        "fullname", fullname, _range, _page)


@app.get("/get_dates_from_id", tags=["id api"])
async def get_dates_from_id(
    _id: str = "19439882",
    _range: int = 7,
    _page: int = 1
):
    """
    取得可能なデータ日時をページ単位で取得します。\n
    返り値はリストです。
    """
    return await items.get_dates_from_mainkey("id", _id, _range, _page)


@app.get("/get_latest_data_from_fullname", tags=["fullname api"])
async def get_latest_data_from_fullname(fullname: str = "scp-173"):
    """
    最新のデータを取得します。\n
    返り値は辞書です。
    """
    return await items.get_latest_data_from_fullname(fullname)


@app.get("/get_latest_data_from_id", tags=["id api"])
async def get_latest_data_from_id(_id: str = "19439882"):
    """
    最新のデータを取得します。\n
    返り値は辞書です。該当がなければnullです。
    """
    return await items.search_tag_collection.find_one({"id": _id}, {"_id": 0})


@app.get("/get_data_from_fullname_and_date", tags=["fullname api"])
async def get_data_from_fullname_and_date(
    fullname: str = "scp-173",
    date: str = "2020-xx-xx"
):
    """
    指定された日付のデータを取得します。\n
    返り値は辞書です。該当がなければnullです。
    """
    return await items.get_data_from_mainkey_and_date(
        "fullname", fullname, date)


@app.get("/get_data_from_id_and_date", tags=["id api"])
async def get_data_from_id_and_date(
    _id: str = "19439882",
    date: str = "2020-xx-xx"
):
    """
    指定された日付のデータを取得します。\n
    返り値は辞書です。該当がなければnullです。
    """
    return await items.get_data_from_mainkey_and_date("id", _id, date)


@app.get("/get_rate_from_fullname_during_the_period", tags=["fullname api"])
async def get_rate_from_fullname_during_the_period(
    fullname: str = "scp-173",
    start: str = "2020-xx-xx",
    stop: str = "2020-xx-xx"
):
    """
    指定された区間のrateデータを取得します。\n
    最大参照日数は366日です。\n
    返り値は辞書です。
    """
    return await items.get_rate_from_mainkey_during_the_period(
        "fullname", fullname, start, stop)


@app.get("/get_rate_from_id_during_the_period", tags=["id api"])
async def get_rate_from_id_during_the_period(
    _id: str = "19439882",
    start: str = "2020-xx-xx",
    stop: str = "2020-xx-xx"
):
    """
    指定された区間のrateデータを取得します。\n
    最大参照日数は366日です。\n
    返り値は辞書です。
    """
    return await items.get_rate_from_mainkey_during_the_period(
        "id", _id, start, stop)


@app.get("/get_all_fullname", tags=["fullname api"])
async def get_all_fullname(_range: int = 10, _page: int = 1):
    """
    利用可能なキーをページを指定して取得します。\n
    返り値はリストです。
    """
    return await items.get_all_mainkey("fullname", _range, _page)


@app.get("/get_all_id", tags=["id api"])
async def get_all_id(_range: int = 10, _page: int = 1):
    """
    利用可能なキーをページを指定して取得します。\n
    返り値はリストです。
    """
    return await items.get_all_mainkey("id", _range, _page)


@app.get("/test")
async def test():
    return await items.test()


@app.get("/get_id_during_time_from_created_at", tags=["akanesasu api"])
async def get_id_during_time_from_created_at(
        start: str = "2020-xx-xx",
        stop: str = "2020-xx-xx"):
    """
    指定された期間内に作成された記事のidを返します。
    """
    return await items.get_id_during_time_from_created_at(start, stop)


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
