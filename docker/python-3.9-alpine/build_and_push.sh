#! /bin/sh

docker build -t yoyonel/python:3.7-alpine3.9 .
docker push yoyonel/python:3.7-alpine3.9
