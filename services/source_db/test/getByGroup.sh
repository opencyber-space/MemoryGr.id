#!/bin/bash

curl -d '{"groupID": "chennai-group"}' -H "Content-Type:application/json" \
    http://localhost:4001/api/getSourcesByGroup