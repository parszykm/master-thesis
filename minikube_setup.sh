#!/bin/bash
set -euo pipefail

BUILD_TYPE=${1:-istio}

minikube start --memory=8192 --cpus=4 --driver=docker

minikube addons enable ingress
minikube addons enable metrics-server

if [ "$BUILD_TYPE" = "istio" ]; then
  minikube addons enable istio-provisioner
  minikube addons enable istio
elif [ "$BUILD_TYPE" = "cilium" ]; then
  helm repo add cilium https://helm.cilium.io
  helm repo update
  helm upgrade --install cilium cilium/cilium \
    --namespace kube-system --create-namespace \
    --set hubble.relay.enabled=true \
    --set hubble.ui.enabled=true
fi

# Monitoring
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

helm upgrade --install prometheus prometheus-community/prometheus \
  --namespace monitoring --create-namespace

helm upgrade --install grafana grafana/grafana \
  --namespace monitoring --create-namespace
