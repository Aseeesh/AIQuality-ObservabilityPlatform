# AI Quality & Observability Platform — common developer tasks
.PHONY: help up down dev prod build test eval clean

help:
	@echo "Targets: up down dev prod build test eval clean"

up:                       ## Start base dev stack
	docker compose -f docker/docker-compose.yml up -d

dev:                      ## Start dev stack (hot reload)
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up

prod:                     ## Start production-like stack
	docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d

down:                     ## Stop everything
	docker compose -f docker/docker-compose.yml down

build:                    ## Build backend + frontend
	dotnet build backend
	cd frontend/quality-platform && npm run build

test:                     ## Run backend + python tests
	dotnet test backend
	@echo "TODO: pytest python-services"

eval:                     ## Run an evaluation pass
	./scripts/run-evaluation.sh

clean:
	docker compose -f docker/docker-compose.yml down -v
