#!/bin/bash
cd `dirname $0`
./build.sh
#docker service update --image python:3.8-alpine being24_api_apiserver
docker service update --image  ayame_fastapi being24_api_apiserver
docker service update --image mongo   being24_api_mongodb
docker service update --image mongo-express   being24_api_mongo-express
