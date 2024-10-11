#!/bin/bash
set -e

if [ -f .env ]; then
    echo "Using .env file environment variable overrides"
    . .env
fi

CUR_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$CUR_DIR" || exit

HOST_ADDRESS=$(ifconfig | grep "inet " | grep -v "127.0" | awk '{print $2}' | head -n 1)

if [[ "$HOST_ADDRESS" == "" ]]; then
    echo "Could not determine host address. Make sure you have 'ifconfig' (net-tools) installed" >&2
    exit 1
fi

# control if and how we want to start the all-in-one backend
AIO_START=${AIO_START:-1}
AIO_TAG=${AIO_TAG_OVERRIDE:-${AIO_TAG:-dev}} # if want to use particular branch, set branch name here
AIO_PORT=${AIO_PORT:-8888}
AIO_STUDIO_TAG=${AIO_STUDIO_TAG_OVERRIDE:-${AIO_STUDIO_TAG:-dev}} # if want to use particular branch, set branch name here
AIO_STUDIO_PATH=${AIO_STUDIO_PATH:-""} # if set, serves studio from this path. should point to a `build` directory
BASE_URL=${BASE_URL:-"http://127.0.0.1:8888"}
ZIA_PATH=${ZIA_PATH:-"../zia_proxy.sh"}
ENV=${ENV:-"aio"}

# if set, don't mount ~/.config/gcloud, but use service account specified in this file
GOOGLE_APPLICATION_CREDENTIALS=${GOOGLE_APPLICATION_CREDENTIALS:-""}

EMBEDDING_K8S_FORWARD=${EMBEDDING_K8S_FORWARD:-1} # if enabled, forward embedding service from a k8s deployment
EMBEDDING_K8S_NAMESPACE=${EMBEDDING_K8S_NAMESPACE:-staging2}
EMBEDDING_SERVICE=${EMBEDDING_SERVICE:-""} # if set, use this address for embeddings

if [ -f "aio_logs/env.log" ]; then
    echo "removing previous env log"
    rm aio_logs/env.log
fi

set | grep "^AIO_.*TAG" >> aio_logs/env.log

function cleanup {
    if [[ $AIO_STARTED -eq 1 ]]; then
        echo "Stopping AIO..."
        docker rm -f aio || true
        sudo kill -9 $(sudo lsof -t -i :8501) || true &>/dev/null
    fi

}
trap cleanup EXIT

AIO_STARTED=0
function start_aio() {
    echo "Starting AIO..."

    DOCKER_ARGS=(-p "${AIO_PORT}:8888")
    AIO_ARGS=()

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

    if [[ -n "$AIO_STUDIO_PATH" ]]; then
        AIO_ARGS=("${AIO_ARGS[@]}" --ui-path "$AIO_STUDIO_PATH")
    else
        AIO_ARGS=("${AIO_ARGS[@]}" --ui-tag "$AIO_STUDIO_TAG")
    fi

    docker pull "gcr.io/trial-184203/backend-aio:$AIO_TAG" # fetch sync

    docker rm -f aio 2&> /dev/null || true # remove previous container if exists

    docker run --name aio -d \
        -p 50051:50051 \
        "${DOCKER_ARGS[@]}" \
        "gcr.io/trial-184203/backend-aio:$AIO_TAG" \
        "${AIO_ARGS[@]}"

    if [ -f "aio_logs/aio.log" ]; then
        echo "removing previous aio log"
        rm aio_logs/aio.log
    fi

    # send aio logs to file in case of failure
    docker aio_logs -f aio >aio_logs/aio.log 2>&1 &

    AIO_STARTED=1
}


EMBEDDINGS_PID=0
function k8s_forward_embeddings() {
    echo "Forwarding embeddings..."
    kubectl -n "${EMBEDDING_K8S_NAMESPACE}" get deployment/embeddings &>/dev/null # try to get deployment first, it will fail if something isn't configured
    kubectl -n "${EMBEDDING_K8S_NAMESPACE}" port-forward deployment/embeddings 8501:50051 --address 0.0.0.0 &>/dev/null &
    EMBEDDINGS_PID=$!
}

function validate_test_params() {
    if [[ -z "$CRED_EMAIL" || -z "$CRED_PASSWORD" ]]; then
        echo "CRED_EMAIL and CRED_PASSWORD must be set" >&2
        exit 1
    fi

    if [[ -z "$BASE_URL" ]]; then
        echo "BASE_URL must be set" >&2
        exit 1
    fi
    echo "Using BASE_URL ${BASE_URL}"
    export BASE_URL=${BASE_URL}

    if [[ -z "$ENV" ]]; then
        echo "ENV must be set" >&2
        exit 1
    fi
    echo "Using ENV ${ENV}"
    export ENV=${ENV}
    if [[ -z "$ZIA_PATH" ]]; then
        echo "ZIA_PATH must be set" >&2
        exit 1
    fi
    echo "Using ZIA_PATH ${ZIA_PATH}"
    export ZIA_PATH=${ZIA_PATH}

}



COMMAND=${1:-test}
case $COMMAND in
test)
    # validate_test_params
    
    if [[ $EMBEDDING_K8S_FORWARD -eq 1 ]]; then
        k8s_forward_embeddings
    fi
    if [[ $AIO_START -eq 1 ]]; then
        start_aio
    fi

    pytest -s --cov ./humanfirst/ --cov-report term # pytest command

    ;;

start-aio)
    if [[ $EMBEDDING_K8S_FORWARD -eq 1 ]]; then
        k8s_forward_embeddings
    fi

    start_aio
    echo "Press any key to stop AIO..."
    read
    ;;

*)
    echo "unknown command: '$COMMAND'" >&2
    exit 1
    ;;
esac

