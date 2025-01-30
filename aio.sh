#!/bin/bash
#set -e

# ******************************************************************************
# This script is used to start and stop the AIO container
# The AIO container is used to run the end-to-end tests
# ******************************************************************************

AIO_TAG=${AIO_TAG_OVERRIDE:-${AIO_TAG:-dev}}                         # backend tag to use
AIO_STUDIO_TAG=${AIO_STUDIO_TAG_OVERRIDE:-${AIO_STUDIO_TAG:-dev}}    # playbooks tag to use
AIO_STUDIO_PATH=${AIO_STUDIO_PATH:-""}                               # if set, serves studio from this path. should point to a `build` directory
GOOGLE_APPLICATION_CREDENTIALS=${GOOGLE_APPLICATION_CREDENTIALS:-""} # if set, don't mount ~/.config/gcloud, but use service account specified in this file
EMBEDDING_K8S_FORWARD=${EMBEDDING_K8S_FORWARD:-1}                    # if enabled, forward embedding service from a k8s deployment
EMBEDDING_K8S_NAMESPACE=${EMBEDDING_K8S_NAMESPACE:-staging2}
EMBEDDING_SERVICE=${EMBEDDING_SERVICE:-""} # if set, use this address for embeddings

function check_dependencies() {
    DOCKER_VERSION=$(docker --version)
    if [[ $DOCKER_VERSION != "Docker version"* ]]; then
        echo "Docker is not installed. Please install Docker to run the aio"
        exit 1
    fi

    if [[ $CI != "true" ]]; then
        DOCKER_DESKTOP_VERSION=$(docker desktop version)
        if [[ $DOCKER_DESKTOP_VERSION != "Docker Desktop"* ]]; then
            echo "Docker Desktop is not installed. Please install Docker Desktop to run the aio"
            exit 1
        fi

        ROSETTA_SETTING="$(grep '"useVirtualizationFrameworkRosetta":' "/Users/${USER}/Library/Group Containers/group.com.docker/settings.json")"
        if [[ $ROSETTA_SETTING == *"true"* ]]; then
            echo "Please disable 'Use Rosetta for x86_64/amd64 emulation on Apple Silicon' in Docker Desktop before running aio."
            exit 1
        fi
    fi

    KUBECTL_VERSION=$(kubectl version)
    if [[ $KUBECTL_VERSION != "Client Version"* ]]; then
        echo "kubectl is not installed. Please install kubectl to run the aio"
        exit 1
    fi

    HOST_ADDRESS=$(ifconfig | grep "inet " | grep -v "127.0" | awk '{print $2}' | head -n 1)
    if [[ $HOST_ADDRESS == "" ]]; then
        echo "Could not determine host address. Make sure you have 'ifconfig' (net-tools) installed"
        exit 1
    fi
}

function set_docker_args() {
    DOCKER_ARGS=(-p "8888:8888")

    if [[ -n "$EMBEDDING_SERVICE" ]]; then
        DOCKER_ARGS=("${DOCKER_ARGS[@]}" -e "EMBEDDINGS_SERVICE=${EMBEDDING_SERVICE}")
    elif [[ -n "$EMBEDDING_K8S_FORWARD" ]]; then
        DOCKER_ARGS=("${DOCKER_ARGS[@]}" -e "EMBEDDINGS_SERVICE=${HOST_ADDRESS}:8501")
    else
        echo "No embeddings address specified"
        exit 1
    fi

    if [[ -n "$GOOGLE_APPLICATION_CREDENTIALS" ]]; then
        cp "$GOOGLE_APPLICATION_CREDENTIALS" "$HOME/.config/gcloud/application_default_credentials.json"
        DOCKER_ARGS=("${DOCKER_ARGS[@]}" -v "$GOOGLE_APPLICATION_CREDENTIALS:/root/.config/gcloud/application_default_credentials.json")
    else
        DOCKER_ARGS=("${DOCKER_ARGS[@]}" -v "$HOME/.config/gcloud:/root/.config/gcloud")
    fi

    # mount home directory so that test data files can be accessible in the aio container
    DOCKER_ARGS=("${DOCKER_ARGS[@]}" -v "${HOME}:${HOME}")
}

function set_aio_args() {
    AIO_ARGS=()
    if [[ -n "$AIO_STUDIO_PATH" ]]; then
        AIO_ARGS=("${AIO_ARGS[@]}" --ui-path "$AIO_STUDIO_PATH")
    else
        AIO_ARGS=("${AIO_ARGS[@]}" --ui-tag "$AIO_STUDIO_TAG")
    fi
}

function run_container() {
    AIO_UPTIME="$(docker container ls --filter="NAME=aio" --format="{{.Status}}")"
    if [[ "$(docker container ls --filter="NAME=aio" --format="{{.Status}}")" ]]; then
        echo "AIO container is already running..."
    else

        echo "Starting AIO..."

        docker run --name aio -d \
            -p 50051:50051 \
            "${DOCKER_ARGS[@]}" \
            "gcr.io/trial-184203/backend-aio:$AIO_TAG" \
            "${AIO_ARGS[@]}"

        echo "Redirecting AIO logs..."
        # send aio logs to file in case of failure
        docker logs -f aio &>src/logs/aio.log &

        echo "AIO is running..."
    fi
}

function close() {
    echo "Stopping AIO..."
    docker stop aio
    docker rm -f aio || true

    echo "Stopping embeddings..."
    pkill -f "kubectl -n ${EMBEDDING_K8S_NAMESPACE} port-forward deployment/embeddings 8501:50051 --address" || true
}

function k8s_forward_embeddings() {
    if [[ $EMBEDDING_K8S_FORWARD -eq 1 ]]; then
        echo "Forwarding embeddings..."
        kubectl -n "${EMBEDDING_K8S_NAMESPACE}" get deployment/embeddings # try to get deployment first, it will fail if something isn't configured
        kubectl -n "${EMBEDDING_K8S_NAMESPACE}" port-forward deployment/embeddings 8501:50051 --address 0.0.0.0 2>&1 &
    fi
}

function update_aio_container() {
    echo "Pulling latest AIO image and removing old container..."
    docker pull "gcr.io/trial-184203/backend-aio:$AIO_TAG" # fetch sync
    docker rm -f aio 2 &>/dev/null || true                 # remove previous container if exists
}

function start_docker_desktop() {
    if [[ $CI != "true" ]]; then
        if [[ $(docker ps -q | wc -l) -eq 0 ]]; then
            echo "Starting Docker..."
            open --background -a Docker
            sleep 10
        fi
    fi
}

check_dependencies

COMMAND=${1:-test}
case $COMMAND in
start)

    start_docker_desktop

    k8s_forward_embeddings

    set_docker_args

    set_aio_args

    update_aio_container

    run_container
    ;;

stop)
    close
    ;;
*) ;;
esac
