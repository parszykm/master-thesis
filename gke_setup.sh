#!/bin/bash

set -euo pipefail

# ==============================================================================
# Script Configuration
# ==============================================================================
# This script sets up a GKE cluster, installs Cilium using its CLI,
# and then installs Istio using the istioctl command-line tool.

export PROJECT_ID=$(gcloud config get-value project)
export CLUSTER_NAME="master-thesis-gke"
export REGION="us-central1"
export ZONE="us-central1-a"

BUILD_TYPE=${1:-istio}
ISTIO_VERSION="1.22.1"

MACHINE_TYPE="n2-highcpu-8"
NUM_NODES="4"

# ==============================================================================
# Helper Functions
# ==============================================================================

print_header() {
  echo
  echo "=============================================================================="
  echo "=> $1"
  echo "=============================================================================="
}

# ==============================================================================
# Cluster Creation
# ==============================================================================

print_header "Creating a Standard GKE Cluster: $CLUSTER_NAME"
echo "This may take several minutes..."

if ! gcloud container clusters describe "$CLUSTER_NAME" --zone "$ZONE" &>/dev/null; then
  echo "Enabling required Google Cloud services..."
  gcloud services enable --project="$PROJECT_ID" \
    container.googleapis.com \
    gkehub.googleapis.com

  if [ "$BUILD_TYPE" == "istio" ]; then
    gcloud container clusters create "$CLUSTER_NAME" \
        --project "$PROJECT_ID" \
        --zone "$ZONE" \
        --machine-type "$MACHINE_TYPE" \
        --num-nodes "$NUM_NODES" \
        --workload-pool "${PROJECT_ID}.svc.id.goog" \
        --release-channel "regular" \
        --enable-ip-alias
   elif [ "$BUILD_TYPE" == "cilium" ]; then 
    gcloud container clusters create "$CLUSTER_NAME" \
        --project "$PROJECT_ID" \
        --zone "$ZONE" \
        --machine-type "$MACHINE_TYPE" \
        --num-nodes "$NUM_NODES" \
        --workload-pool "${PROJECT_ID}.svc.id.goog" \
        --release-channel "regular" \
        --node-taints node.cilium.io/agent-not-ready=true:NoExecute \
        --enable-ip-alias
    else
      echo "Not supported BUILD_TYPE = $BUILD_TYPE"
      exit 1
    fi

  echo "Cluster '$CLUSTER_NAME' created successfully."
else
  echo "Cluster '$CLUSTER_NAME' already exists. Skipping creation."
fi

# ==============================================================================
# Configure Kubectl
# ==============================================================================

print_header "Configuring kubectl to connect to $CLUSTER_NAME"
gcloud container clusters get-credentials "$CLUSTER_NAME" --zone "$ZONE" --project "$PROJECT_ID"
echo "kubectl is now configured."

if [ "$BUILD_TYPE" == "cilium" ]; then
    # ==============================================================================
    # CNI Installation (Cilium CLI)
    # ==============================================================================

    print_header "Installing Cilium with the Cilium CLI"

    if ! command -v cilium &> /dev/null; then
        echo "Cilium CLI not found. Downloading..."
        CILIUM_CLI_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/cilium-cli/main/stable.txt)
        CLI_ARCH=arm64
        if [ "$(uname -m)" = "aarch64" ]; then CLI_ARCH=arm64; fi
        curl -L --fail --remote-name-all https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-linux-${CLI_ARCH}.tar.gz{,.sha256sum}
        sha256sum --check cilium-linux-${CLI_ARCH}.tar.gz.sha256sum
        sudo tar xzvfC cilium-linux-${CLI_ARCH}.tar.gz /usr/local/bin
        rm cilium-linux-${CLI_ARCH}.tar.gz{,.sha256sum}
    else
        echo "Cilium CLI is already installed."
    fi

    if [ -f "cilium-values.yaml" ]; then
    print_header "Installing Cilium with values from cilium-values.yaml"
    cilium install --set cluster.name=$CLUSTER_NAME -f cilium-values.yaml
    else
    print_header "Installing Cilium with default values"
    echo "Warning: 'cilium-values.yaml' not found. Installing with defaults."
    cilium install --set cluster.name=$CLUSTER_NAME
    fi

    print_header "Enabling Hubble UI"
    cilium hubble enable --ui
elif [ "$BUILD_TYPE" == "istio" ]; then
    # ==============================================================================
    # Service Mesh Installation (Istio via istioctl)
    # ==============================================================================
    print_header "Installing Istio $ISTIO_VERSION with istioctl"

    if [ ! -d "istio-${ISTIO_VERSION}" ]; then
        echo "Downloading Istio v${ISTIO_VERSION}..."
        curl -L https://istio.io/downloadIstio | ISTIO_VERSION=$ISTIO_VERSION sh -
    else
        echo "Istio v${ISTIO_VERSION} directory already exists. Skipping download."
    fi

    export PATH=$PWD/istio-$ISTIO_VERSION/bin:$PATH
    echo "istioctl added to PATH."

    istioctl install --set profile=default -y --set values.global.platform=gke

    print_header "Enabling Istio sidecar injection for the 'default' namespace"
    kubectl label namespace default istio-injection=enabled --overwrite
fi

# ==============================================================================
# Monitoring Stack Installation (Prometheus & Grafana)
# ==============================================================================

print_header "Installing Monitoring Stack: Prometheus & Grafana"

# Add Helm repositories
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts || echo "Repo 'prometheus-community' already exists."
helm repo add grafana https://grafana.github.io/helm-charts || echo "Repo 'grafana' already exists."
helm repo update

# Install Prometheus
print_header "Installing Prometheus"
helm upgrade --install prometheus prometheus-community/prometheus \
  --namespace monitoring --create-namespace -f prometheus-values.yaml

# Install Grafana
if [ -f "grafana-values-2.yaml" ]; then
  print_header "Installing Grafana with values from grafana-values-2.yaml"
  helm upgrade --install grafana grafana/grafana \
    --namespace monitoring --create-namespace \
    -f grafana-values-3.yaml
else
  print_header "Installing Grafana with default values"
  echo "Warning: 'grafana-values-2.yaml' not found. Installing with defaults."
  helm upgrade --install grafana grafana/grafana \
    --namespace monitoring --create-namespace
fi

print_header "Setup Complete!"
echo "Cluster '$CLUSTER_NAME' is ready."
echo "CNI: Cilium installed via the Cilium CLI with Hubble enabled."
echo "Service Mesh: Istio v$ISTIO_VERSION installed via istioctl."
echo "Run 'cilium status' to check Cilium health."
echo "Run 'kubectl get pods -n istio-system' to check the status of your Istio control plane."
