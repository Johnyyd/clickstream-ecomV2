#!/bin/bash

# Production deployment script for Clickstream EcomV2

# Load environment variables
source .env.prod

# Check requirements
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting." >&2; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "kubectl is required but not installed. Aborting." >&2; exit 1; }

# Build Docker image
echo "Building Docker image..."
docker build -t clickstream-ecomv2:latest .

# Push to container registry
echo "Pushing to container registry..."
docker tag clickstream-ecomv2:latest $CONTAINER_REGISTRY/clickstream-ecomv2:latest
docker push $CONTAINER_REGISTRY/clickstream-ecomv2:latest

# Apply Kubernetes configurations
echo "Applying Kubernetes configurations..."
kubectl apply -f k8s/namespace.yml
kubectl apply -f k8s/configmap.yml
kubectl apply -f k8s/secret.yml
kubectl apply -f k8s/mongodb.yml
kubectl apply -f k8s/kafka.yml
kubectl apply -f k8s/spark.yml
kubectl apply -f k8s/api.yml

# Wait for deployments
echo "Waiting for deployments to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/clickstream-api
kubectl wait --for=condition=available --timeout=300s deployment/spark-master
kubectl wait --for=condition=available --timeout=300s deployment/spark-worker

# Create database indexes
echo "Creating database indexes..."
kubectl exec deploy/clickstream-api -- python -c "from app.repositories.indexes import ensure_indexes; import asyncio; asyncio.run(ensure_indexes())"

# Run database migrations if needed
echo "Running database migrations..."
kubectl exec deploy/clickstream-api -- python scripts/migrate.py

# Verify deployment
echo "Verifying deployment..."
kubectl get pods
kubectl get services

echo "Deployment completed successfully!"