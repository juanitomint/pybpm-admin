IMAGE_REPOSITORY  ?= juanitomint/pybpm-admin
CURRENT_DIR = $(shell pwd)
GIT_LAST_TAG=$(shell git tag --sort=committerdate|tail -n 1)
GIT_COMMIT=$(shell git rev-parse --short HEAD)
IMAGE_TAG ?= $(if $(GIT_LAST_TAG),$(GIT_LAST_TAG),$(GIT_COMMIT))
help:
	@grep -E '^[\/a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
.PHONY: deps
deps: ## Install dependencies using uv
	uv sync --dev

.PHONY: run
run: ## Run the FastAPI development server locally
	-@fuser -k 8080/tcp
	.venv/bin/python -m uvicorn main:app --reload --port 8080

.PHONY: test
test: ## Run all tests
	.venv/bin/python -m pytest

.PHONY: lint
lint: ## Show code lints using ruff
	uv run --with ruff ruff check . --select E,F,W,C90,N,B,SIM,RUF,UP,I

.PHONY: fix
fix: ## Fix code lints using ruff
	uv run --with ruff ruff check --fix .
	uv run --with ruff ruff format ./

.PHONY: docker-build
docker-build: ## Build docker image using latest as cache
	echo "building: ${IMAGE_REPOSITORY}:${IMAGE_TAG}"
	DOCKER_BUILDKIT=1 docker build -t ${IMAGE_REPOSITORY}:latest . --build-arg IMAGE_TAG=${IMAGE_TAG}
	docker tag ${IMAGE_REPOSITORY}:latest ${IMAGE_REPOSITORY}:${IMAGE_TAG}

.PHONY: docker-push
docker-push: ## Push docker image to remote ${IMAGE_REPOSITORY}
	docker push ${IMAGE_REPOSITORY}:${IMAGE_TAG}
	docker push ${IMAGE_REPOSITORY}:latest

.PHONY: docker-test
docker-test: ## Test using docker image with .env variables
	docker run -it --rm -v ${CURRENT_DIR}:/workspace --env-file .env --net=host ${IMAGE_REPOSITORY}:latest

.PHONY: docker-shell
docker-shell: ## Test using docker image with .env variables and execute shell
	docker run -it --rm -v ${CURRENT_DIR}:/workspace --env-file .env --net=host ${IMAGE_REPOSITORY}:latest bash


.PHONY: info
info: ## Print admin build info and status
	@echo "=== pybpm-admin ==="
	@echo "Image repository : $(IMAGE_REPOSITORY)"
	@echo "Last git tag     : $(GIT_LAST_TAG)"
	@echo "Git commit       : $(GIT_COMMIT)"
	@echo ""
	@echo "--- Container status ---"
	@docker ps --filter name=pybpm-admin --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || true

.PHONY: clean
clean: ## Remove admin container and dangling images
	rm -rf ./.venv
	rm -rf ./.pytest_cache
	rm -rf ./**/__pycache__
	rm -f .coverage
	rm -rf htmlcov

.PHONY: printvars
printvars: ## Prints make variables
	$(foreach V, $(sort $(.VARIABLES)), \
	$(if $(filter-out environment% default automatic, $(origin $V)),$(warning $V=$($V) ($(value $V)))) \
	)
