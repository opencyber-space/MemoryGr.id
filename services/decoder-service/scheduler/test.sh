#!/bin/bash

curl -X POST -d '{"node": "framedb-4", "gpuID": 0}' -H "Content-Type:application/json" \
    http://localhost:5000/queryHealth