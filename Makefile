# AI Quality & Observability Platform — developer & operator tasks.
#
# Typical first run (Docker + local Ollama):
#   make start          # build + up + pull the Ollama model + smoke test
# Or step by step:
#   make up  →  make ollama-pull  →  make smoke
#
# Override the local model:  make ollama-pull JUDGE_MODEL=llama3.1

COMPOSE      := docker compose -f docker/docker-compose.yml
COMPOSE_DEV  := $(COMPOSE) -f docker/docker-compose.dev.yml
COMPOSE_PROD := $(COMPOSE) -f docker/docker-compose.prod.yml
JUDGE_MODEL  ?= llama3.2
API          ?= http://localhost:8080
EVAL         ?= http://localhost:8001

.PHONY: help start up down dev prod build rebuild ps logs ollama-pull ollama-list \
        smoke test test-dotnet test-python test-framework eval clean env

help:            ## Show available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

env:             ## Create .env from the example if missing
	@test -f .env || (cp .env.example .env && echo "created .env from .env.example")

# ---------------------------------------------------------------- run the stack
start: env up ollama-pull smoke  ## Build, start everything, pull the model, and smoke test

up: env           ## Build images and start the full stack (Ollama + services + UI)
	$(COMPOSE) up -d --build
	@echo ""
	@echo "  UI        http://localhost:3000"
	@echo "  API       $(API)     (swagger-free; see docs/api)"
	@echo "  Jaeger    http://localhost:16686"
	@echo "  Grafana   http://localhost:3001"
	@echo "  Next: 'make ollama-pull' (first run) then 'make smoke'"

dev: env          ## Start with the Vite dev server (hot reload) in the foreground
	$(COMPOSE_DEV) up --build

prod: env         ## Start the production-like stack (restart policies)
	$(COMPOSE_PROD) up -d --build

down:             ## Stop the stack
	$(COMPOSE) down

ps:               ## Show running services
	$(COMPOSE) ps

logs:             ## Tail logs (all services)
	$(COMPOSE) logs -f --tail=100

rebuild:          ## Rebuild images without cache
	$(COMPOSE) build --no-cache

# ---------------------------------------------------------------- ollama
ollama-pull:      ## Pull the local model into the Ollama container ($(JUDGE_MODEL))
	$(COMPOSE) up -d ollama
	@echo "waiting for ollama…"; \
	until $(COMPOSE) exec -T ollama ollama list >/dev/null 2>&1; do sleep 1; done; \
	echo "pulling $(JUDGE_MODEL) (first time downloads a few GB)…"; \
	$(COMPOSE) exec -T ollama ollama pull $(JUDGE_MODEL)

ollama-list:      ## List models available in the Ollama container
	$(COMPOSE) exec -T ollama ollama list

# ---------------------------------------------------------------- verify
smoke:            ## Smoke-test the running stack (API + judge + demos)
	./scripts/smoke-test.sh

# ---------------------------------------------------------------- tests
test: test-dotnet test-python test-framework  ## Run the full test suite

test-dotnet:      ## .NET unit tests (31)
	dotnet test backend/AIQuality.sln

test-python:      ## Python per-service unit suites (50)
	./scripts/run-python-tests.sh

test-framework:   ## Cross-cutting framework suites (10)
	./tests/run-tests.sh

eval:             ## Run an offline evaluation pass (heuristic backend)
	./scripts/run-evaluation.sh

# ---------------------------------------------------------------- cleanup
clean:            ## Stop and remove volumes (Ollama models, Postgres data)
	$(COMPOSE) down -v
