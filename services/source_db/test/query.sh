#!/bin/bash

curl -d '{"query": {"sourceType": "live"}}' -H "Content-Type:application/json" \
    http://localhost:4001/api/query