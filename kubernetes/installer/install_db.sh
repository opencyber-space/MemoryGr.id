#!/bin/bash

# USAGE: ./deploy_framedb.sh <replica-count> [storage-size]
REPLICAS=$1
STORAGE=${2:-1Gi}
NAMESPACE="framedb-db"

if [[ -z "$REPLICAS" ]]; then
  echo "Usage: $0 <replica-count> [storage-size]"
  exit 1
fi

echo "Deploying $REPLICAS FrameDB replica nodes with $STORAGE storage each in namespace '$NAMESPACE'..."

# Create namespace
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Step 1: Create PVs, PVCs, Deployments, and Services per replica
for i in $(seq 0 $((REPLICAS - 1))); do
  echo "🔧 Setting up framedb-$i..."

  # Create PersistentVolume
  cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolume
metadata:
  name: framedb-pv-$i
  labels:
    volume-id: framedb-$i
spec:
  capacity:
    storage: $STORAGE
  accessModes:
    - ReadWriteOnce
  storageClassName: ""
  hostPath:
    path: /mnt/data/framedb-$i
  persistentVolumeReclaimPolicy: Retain
  nodeAffinity:
    required:
      nodeSelectorTerms:
        - matchExpressions:
            - key: framedb
              operator: In
              values:
                - "yes"
EOF

  # Create PersistentVolumeClaim
  cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: framedb-pvc-$i
  namespace: $NAMESPACE
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: ""
  volumeName: framedb-pv-$i
  resources:
    requests:
      storage: $STORAGE
EOF

  # Create Deployment
  cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: framedb-$i
  namespace: $NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: framedb-$i
  template:
    metadata:
      labels:
        app: framedb-$i
    spec:
      containers:
        - name: mongo
          image: mongo:6.0
          command:
            - mongod
            - "--replSet"
            - rs0
            - "--bind_ip_all"
          ports:
            - containerPort: 27017
          volumeMounts:
            - name: data
              mountPath: /data/db
      volumes:
        - name: data
          persistentVolumeClaim:
            claimName: framedb-pvc-$i
EOF

  # Create Service
  cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Service
metadata:
  name: framedb-$i
  namespace: $NAMESPACE
spec:
  selector:
    app: framedb-$i
  ports:
    - port: 27017
      targetPort: 27017
EOF

done

# Step 2: ConfigMap with init.js for rs.initiate
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: framedb-init
  namespace: $NAMESPACE
data:
  init.js: |
    rs.initiate({
      _id: "rs0",
      members: [
$(for i in $(seq 0 $((REPLICAS - 1))); do
echo "        { _id: $i, host: \"framedb-$i.$NAMESPACE.svc.cluster.local:27017\" }$( [[ $i -lt $((REPLICAS - 1)) ]] && echo "," )"
done)
      ]
    });
EOF

# Step 3: Initialization Client Pod
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: framedb-init-client
  namespace: $NAMESPACE
spec:
  restartPolicy: Never
  containers:
    - name: mongo
      image: mongo:5.0
      command:
        - sh
        - -c
        - |
          echo "Waiting for framedb-0 to be reachable..."
          until mongo --host framedb-0.$NAMESPACE.svc.cluster.local --eval "db.adminCommand('ping')" >/dev/null 2>&1; do
            echo "Waiting for Mongo to be ready..."
            sleep 5
          done

          echo "Checking if replica set is already initiated..."
          if ! mongo --host framedb-0.$NAMESPACE.svc.cluster.local --quiet --eval "rs.status().ok" | grep 1 >/dev/null; then
            echo "Running rs.initiate()..."
            mongo --host framedb-0.$NAMESPACE.svc.cluster.local /config/init.js
          else
            echo "Replica set already initialized. Skipping."
          fi
      volumeMounts:
        - name: init-script
          mountPath: /config
  volumes:
    - name: init-script
      configMap:
        name: framedb-init
EOF

echo "✅ FrameDB deployment complete. Run: kubectl get pods -n $NAMESPACE"
