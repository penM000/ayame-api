#!/bin/sh
apk add --no-cache build-base mariadb-connector-c-dev
pip3 install fastapi uvicorn motor 