#!/bin/bash

docker kill gmock
docker rm gmock
docker build -t gmock:latest .
docker run -p 5000:5000 -v $(pwd):/app --name=gmock -t gmock:latest
