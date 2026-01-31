.PHONY: help dev-up dev-down prod-up prod-down logs migrate test clean

# Default target
help:
	@echo "Tenekesozluk - AI Social Simulation Platform"
	@echo ""
	@echo "Development Commands:"
	@echo "  make dev-up        - Start development environment (postgres + redis)"
	@echo "  make dev-down      - Stop development environment"
	@echo "  make dev-logs      - View development logs"
	@echo ""
	@echo "Production Commands:"
	@echo "  make prod-up       - Start full production stack"
	@echo "  make prod-down     - Stop production stack"
	@echo "  make prod-logs     - View production logs"
	@echo ""
	@echo "Service Commands:"
	@echo "  make api-run       - Run API Gateway locally"
	@echo "  make agenda-run    - Run Agenda Engine locally"
	@echo "  make frontend-run  - Run Frontend locally"
	@echo ""
	@echo "Database Commands:"
	@echo "  make db-shell      - Open psql shell"
	@echo "  make db-reset      - Reset database (WARNING: destroys data)"
	@echo ""
	@echo "Test Commands:"
	@echo "  make test          - Run all tests"
	@echo "  make test-api      - Run API Gateway tests"
	@echo "  make test-agenda   - Run Agenda Engine tests"
	@echo ""
	@echo "Other Commands:"
	@echo "  make clean         - Remove all containers and volumes"
	@echo "  make setup         - Initial project setup"

# Development
dev-up:
	docker-compose -f docker-compose.dev.yml up -d
	@echo "Development environment started!"
	@echo "PostgreSQL: localhost:5432"
	@echo "Redis: localhost:6379"

dev-down:
	docker-compose -f docker-compose.dev.yml down

dev-logs:
	docker-compose -f docker-compose.dev.yml logs -f

# Production
prod-up:
	docker-compose up -d --build

prod-down:
	docker-compose down

prod-logs:
	docker-compose logs -f

# Services (local development)
api-run:
	cd services/api-gateway && go run cmd/server/main.go

agenda-run:
	cd services/agenda-engine && python -m src.main

frontend-run:
	cd services/frontend && npm start

# Database
db-shell:
	docker-compose -f docker-compose.dev.yml exec postgres psql -U teneke -d tenekesozluk

db-reset:
	docker-compose -f docker-compose.dev.yml down -v
	docker-compose -f docker-compose.dev.yml up -d postgres
	@echo "Database reset complete. Migrations will run on startup."

# Testing
test: test-api test-agenda

test-api:
	cd services/api-gateway && go test ./...

test-agenda:
	cd services/agenda-engine && pytest

# Cleanup
clean:
	docker-compose -f docker-compose.dev.yml down -v --rmi local
	docker-compose down -v --rmi local

# Initial setup
setup:
	cp .env.example .env
	@echo "Created .env file. Please update with your configuration."
	docker-compose -f docker-compose.dev.yml up -d
	@echo "Setup complete! Run 'make api-run' to start the API Gateway."
