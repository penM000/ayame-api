FROM    python:3.8-alpine
RUN     apk add --no-cache build-base mariadb-connector-c-dev libxml2-dev libxslt-dev snappy-dev &&\
        pip3 install fastapi uvicorn motor aiofiles asyncio bs4 lxml requests python-snappy 
CMD     cd /fastapi && uvicorn main:app --reload --host 0.0.0.0

