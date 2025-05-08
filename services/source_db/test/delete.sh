#!/bin/bash

curl -d '{"sourceID": "source-chennai-123"}' -H "Content-Type:application/json" \
    http://localhost:4001/api/removeBySourceID