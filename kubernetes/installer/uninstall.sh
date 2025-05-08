#!/bin/bash

kubectl delete -f services/
kubectl delete namespace framedb-services
kubectl delete namespace framedb-db

