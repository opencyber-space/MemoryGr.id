#!/bin/bash

curl -d '{"sourceID": "source-chennai-124", "data": {"sourceType": "live"}}' -H "Content-Type:application/json" \
    http://localhost:4001/api/updateSource