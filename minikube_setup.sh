#!/bin/bash
set -euo pipefail

BUILD_TYPE=${1:-istio}

if [ "$BUILD_TYPE" = "istio" ]; then
    minikube start --memory=11934 --cpus=6 --driver=docker
elif [ "$BUILD_TYPE" = "cilium" ]; then
    minikube start --memory=11934 --cpus=6 --driver=docker
fi

minikube addons enable ingress
minikube addons enable metrics-server

if [ "$BUILD_TYPE" = "istio" ]; then
  minikube addons enable istio-provisioner
  minikube addons enable istio
elif [ "$BUILD_TYPE" = "cilium" ]; then
  helm repo add cilium https://helm.cilium.io || echo "Repo https://helm.cilium.io already exists"
  helm repo update
  helm install cilium cilium/cilium \
    --namespace kube-system --create-namespace -f cilium-values.yaml
fi

# Monitoring
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts || echo "Repo https://prometheus-community.github.io/helm-charts already exists"
helm repo add grafana https://grafana.github.io/helm-charts || echo "Repo https://grafana.github.io/helm-charts"
helm repo update

helm upgrade --install prometheus prometheus-community/prometheus \
  --namespace monitoring --create-namespace  --set server.global.scrape_interval="30s"

helm upgrade --install grafana grafana/grafana \
  --namespace monitoring --create-namespace -f grafana-values-2.yaml

