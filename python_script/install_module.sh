#!/bin/sh
apk add --no-cache build-base mariadb-connector-c-dev libxml2-dev libxslt-dev snappy-dev
pip3 install fastapi uvicorn motor aiofiles asyncio bs4 lxml requests python-snappy 