#!/bin/bash

curl -d '{"sourceID": "prasannatest"}' -H "Content-Type:application/json" \
    http://192.168.111.113:32000/sr/api/getBySourceID
