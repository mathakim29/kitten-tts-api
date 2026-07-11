#!/bin/make
IMAGE_NAME = kittentts-cuda-api
PORT = 8000

build:
	podman build -t $(IMAGE_NAME) .

run:
	podman run -v ./src:/src:z -v ./export:/export:z --gpus all -p $(PORT):$(PORT) $(IMAGE_NAME)

test:
	curl -X POST "http://localhost:$(PORT)/generate" \
		-H "Content-Type: application/json" \
		-d '{"text": "Testing the makefile.", "voice": "Bruno"}' \
		--output output.wav

clean:
	podman stop $$(podman ps -q --filter ancestor=$(IMAGE_NAME)) 2>/dev/null || true
	podman rm $$(podman ps -aq --filter ancestor=$(IMAGE_NAME)) 2>/dev/null || true