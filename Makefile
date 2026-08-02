IMAGE_REPOSITORY  ?= juanitomint/pybpm-admin
CURRENT_DIR = $(shell pwd)
GIT_LAST_TAG=$(shell git tag --sort=committerdate|tail -n 1)
GIT_COMMIT=$(shell git rev-parse --short HEAD)

.PHONY: deps
deps: ## Install dependencies using uv
	uv sync --dev

.PHONY: run
run: ## Run the FastAPI development server locally
	.venv/bin/python -m uvicorn main:app --reload --port 8080

.PHONY: migrate
migrate: ## Run database migrations
	.venv/bin/python -m alembic upgrade head

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

.PHONY: stop
stop: ## Stop admin container
	docker compose down admin

.PHONY: logs
logs: ## Show admin container logs (tail, follow mode)
	docker compose logs -f admin

.PHONY: info
info: ## Print admin build info and status
	@echo "=== pybpm-admin ==="
	@echo "Image repository : $(IMAGE_REPOSITORY)"
	@echo "Last git tag     : $(GIT_LAST_TAG)"
	@echo "Git commit       : $(GIT_COMMIT)"
	@echo ""
	@echo "--- Container status ---"
	@docker ps --filter name=pybpm-admin --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || true

.PHONY: compose-up
compose-up: ## Start admin (detached, removes orphaned containers)
	docker compose up -d --remove-orphans

.PHONY: compose-down
compose-down: ## Stop and remove admin containers and resources
	docker compose down --remove-orphans

.PHONY: docker-build
docker-build: ## Build admin image using latest as cache
	echo "building: ${IMAGE_REPOSITORY}:${IMAGE_TAG}"
	DOCKER_BUILDKIT=1 docker build -t ${IMAGE_REPOSITORY}:latest . --build-arg IMAGE_TAG=${IMAGE_TAG}
	docker tag ${IMAGE_REPOSITORY}:latest ${IMAGE_REPOSITORY}:${IMAGE_TAG}

.PHONY: docker-push
docker-push: ## Push admin image to remote ${IMAGE_REPOSITORY}
	docker push ${IMAGE_REPOSITORY}:${IMAGE_TAG}
	docker push ${IMAGE_REPOSITORY}:latest

.PHONY: clean
clean: ## Remove admin container and dangling images
	docker compose down --rmi local --remove-orphans
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
