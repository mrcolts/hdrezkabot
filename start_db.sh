#!/usr/bin/env bash
docker run --rm --name hdrezka-rethink -v /tmp/db_data:/data -p 8080:8080 -p 28015:28015 -p 29015:29015 -d rethinkdb