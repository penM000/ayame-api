FROM    python:3.9-alpine
RUN     apk add --no-cache build-base mariadb-connector-c-dev libxml2-dev libxslt-dev &&\
        pip3 install fastapi uvicorn[standard] motor aiofiles asyncio bs4 lxml requests python-dateutil
WORKDIR /
CMD /bin/bash

