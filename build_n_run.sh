# ...existing code...
#!/usr/bin/env bash

# Set colors
red=$(tput setaf 1)
green=$(tput setaf 2)
yellow=$(tput setaf 3)
blue=$(tput setaf 4)
bold=$(tput bold)
reset=$(tput sgr0)

IMAGE_NAME='myapp'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$SCRIPT_DIR/.cache"

# Determine which container tool to use (auto-detect)
if command -v docker &> /dev/null; then
    DETECTED_TOOL='docker'
elif command -v podman &> /dev/null; then
    DETECTED_TOOL='podman'
else
    echo "${red}${bold}Error:${reset} Neither docker nor podman is installed or enabled"
    exit 1
fi

CONTAINER_TOOL="$DETECTED_TOOL"

# Parse args: --use docker|podman
while [ $# -gt 0 ]; do
    case "$1" in
        --use)
            shift
            if [ "$1" = "docker" ] || [ "$1" = "podman" ]; then
                CONTAINER_TOOL="$1"
            else
                echo "${red}${bold}Error:${reset} --use accepts 'docker' or 'podman'"
                exit 1
            fi
            ;;
        -h|--help)
            echo "Usage: $0 [--use docker|podman]"
            echo "Examples:"
            echo "  $0                # auto-detect docker/podman"
            echo "  $0 --use docker   # force docker"
            echo "  $0 --use podman   # force podman"
            exit 0
            ;;
        *)
            echo "${red}${bold}Error:${reset} Unknown argument: $1"
            exit 1
            ;;
    esac
    shift
done

# Dockerfile content
DOCKERFILE=$(cat <<'EOF'
    FROM docker.io/pytorch/pytorch:2.13.0-cuda13.2-cudnn9-runtime

    RUN apt-get update && apt-get install -y \
    curl \
    git \
    sudo

    RUN curl https://frankenphp.dev/install.sh | sh

    RUN rm -rf /var/lib/apt/lists/*

    RUN pip install --break-system-packages fastapi uvicorn python-multipart 

    RUN pip install --break-system-packages https://github.com/KittenML/KittenTTS/releases/download/0.8.1/kittentts-0.8.1-py3-none-any.whl
EOF
)

# Adjust volume labels for podman
if [ "$CONTAINER_TOOL" = "podman" ]; then
    VOL_LABEL=":Z"
else
    VOL_LABEL=""
fi

CACHE_VOL="$SCRIPT_DIR/.cache/:/root/.cache${VOL_LABEL}"
WORK_VOL="$SCRIPT_DIR:/workspace${VOL_LABEL}"

echo "${green}Using container tool:${reset} $CONTAINER_TOOL"
echo "${blue}Building image:${reset} $IMAGE_NAME"

# Build
echo "$DOCKERFILE" | $CONTAINER_TOOL build -t "${IMAGE_NAME}" -

# Run
$CONTAINER_TOOL run -it --gpus=all -v "$CACHE_VOL" -v "$WORK_VOL" -p 8000:8000 "${IMAGE_NAME}" python3 -m uvicorn api:app --host 0.0.0.0 --reload
