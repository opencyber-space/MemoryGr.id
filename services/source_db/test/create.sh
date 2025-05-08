#!/bin/bash

curl -H "Content-Type:application/json" -d @./create.json \
    http://localhost:4001/api/createNew | json_pp


#curl -H "Content-Type:application/json" -d @./create_2.json \
#    http://localhost:4001/api/createNew | json_pp
