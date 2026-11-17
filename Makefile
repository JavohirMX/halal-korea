# ==============================================================================
# Halal Korea (할랄 코리아) 🇰🇷 - Developer & Operations Makefile
# ==============================================================================

.DEFAULT_GOAL := help
SHELL := /bin/bash

# Detect uv package manager
UV ?= $(shell command -v uv 2>/dev/null)
ifeq ($(UV),)
    $(warning [!] uv is not installed. Falling back to system python. Install uv: https://docs.astral.sh/uv/)
    RUN :=
    PYTHON := python3
    PIP := pip
else
    RUN := uv run
    PYTHON := uv run python
    PIP := uv pip
endif

# Terminal colors for help menu
CYAN    := \033[36m
GREEN   := \033[32m
YELLOW  := \033[33m
BLUE    := \033[34m
MAGENTA := \033[35m
RESET   := \033[0m
BOLD    := \033[1m

.PHONY: help
help: ## Display this interactive help menu
	@echo ""
	@echo -e "${BOLD}${GREEN}Halal Korea 🇰🇷${RESET} - Developer & Operations Automation"
	@echo -e "${YELLOW}Package Manager:${RESET} $(if $(UV),${GREEN}uv (${UV})${RESET},${YELLOW}system python (uv recommended)${RESET})"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage: make ${CYAN}<target>${RESET} [ARG=value]\n"} \
		/^[a-zA-Z0-9_-]+:.*?##/ { printf "  ${CYAN}%-22s${RESET} %s\n", $$1, $$2 } \
		/^##@/ { printf "\n${BOLD}%s${RESET}\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""

##@ 🛠️  Environment & Package Management (uv)

.PHONY: setup
setup: ## Full initial onboarding: verify env, sync dependencies, run migrations
	@echo -e "${BLUE}==>${RESET} Setting up Halal Korea environment..."
	@if [ ! -f .env ]; then \
		echo -e "${YELLOW}Creating .env from .env.example...${RESET}"; \
		cp .env.example .env; \
	fi
	@if [ -n "$(UV)" ]; then \
		echo -e "${GREEN}==>${RESET} Installing dependencies with uv..."; \
		uv sync --all-groups; \
	else \
		pip install -r requirements.txt; \
	fi
	@echo -e "${GREEN}==>${RESET} Setup complete! Run '${CYAN}make dev${RESET}' to start the server."

.PHONY: venv
venv: ## Create or sync the local virtual environment with all dev dependencies
	@echo -e "${BLUE}==>${RESET} Synchronizing virtual environment..."
	@$(if $(UV),uv sync --all-groups,python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt)

.PHONY: install
install: ## Sync production dependencies only
	@echo -e "${BLUE}==>${RESET} Installing production dependencies..."
	@$(if $(UV),uv sync --no-dev,pip install -r requirements.txt)

.PHONY: install-dev
install-dev: ## Sync production and development dependencies (ruff, coverage)
	@echo -e "${BLUE}==>${RESET} Installing all dependencies (including dev)..."
	@$(if $(UV),uv sync --all-groups,pip install -r requirements.txt)

.PHONY: lock
lock: ## Update uv.lock and regenerate requirements.txt
	@echo -e "${BLUE}==>${RESET} Updating uv.lock and synchronizing requirements.txt..."
	@$(if $(UV),uv lock && uv pip compile pyproject.toml -o requirements.txt,echo "uv required to lock dependencies")

.PHONY: add
add: ## Add a production package (usage: make add PKG=requests)
	@if [ -z "$(PKG)" ]; then echo -e "${YELLOW}Usage: make add PKG=<package-name>${RESET}"; exit 1; fi
	@$(if $(UV),uv add $(PKG),pip install $(PKG) && pip freeze > requirements.txt)

.PHONY: add-dev
add-dev: ## Add a development package (usage: make add-dev PKG=pytest)
	@if [ -z "$(PKG)" ]; then echo -e "${YELLOW}Usage: make add-dev PKG=<package-name>${RESET}"; exit 1; fi
	@$(if $(UV),uv add --dev $(PKG),pip install $(PKG))

.PHONY: remove
remove: ## Remove a package (usage: make remove PKG=package)
	@if [ -z "$(PKG)" ]; then echo -e "${YELLOW}Usage: make remove PKG=<package-name>${RESET}"; exit 1; fi
	@$(if $(UV),uv remove $(PKG),pip uninstall -y $(PKG))

.PHONY: sync
sync: ## Sync dependencies strictly matching uv.lock
	@$(if $(UV),uv sync --frozen,pip install -r requirements.txt)

##@ 🚀 Local Development Server

.PHONY: dev run
dev: ## Start Django development server at http://localhost:8000
	@echo -e "${GREEN}==>${RESET} Launching Halal Korea development server..."
	@$(PYTHON) manage.py runserver

run: dev

.PHONY: shell
shell: ## Open Django interactive shell
	@$(PYTHON) manage.py shell

.PHONY: dbshell
dbshell: ## Connect directly to the PostgreSQL database CLI
	@$(PYTHON) manage.py dbshell

.PHONY: check
check: ## Run Django system configuration and model validation checks
	@$(PYTHON) manage.py check

.PHONY: check-deploy
check-deploy: ## Run Django production deployment security checks
	@$(PYTHON) manage.py check --deploy

##@ 🗄️  Database & Seed Data

.PHONY: migrate
migrate: ## Apply pending database migrations
	@echo -e "${BLUE}==>${RESET} Applying database migrations..."
	@$(PYTHON) manage.py migrate

.PHONY: makemigrations
makemigrations: ## Generate new migrations from model changes
	@echo -e "${BLUE}==>${RESET} Generating database migrations..."
	@$(PYTHON) manage.py makemigrations

.PHONY: showmigrations
showmigrations: ## Display migration status across all apps
	@$(PYTHON) manage.py showmigrations

.PHONY: superuser
superuser: ## Create a new Django administrator / superuser
	@$(PYTHON) manage.py createsuperuser

.PHONY: seed
seed: ## Populate sample halal places across South Korea (default: 25)
	@echo -e "${GREEN}==>${RESET} Seeding test places into database..."
	@$(PYTHON) manage.py create_test_data --count $(or $(COUNT),25)

.PHONY: seed-blog
seed-blog: ## Seed sample blog categories and articles
	@echo -e "${GREEN}==>${RESET} Seeding sample blog data..."
	@$(PYTHON) manage.py create_sample_blog_data

.PHONY: populate-search
populate-search: ## Index full-text search data and proximity locations
	@echo -e "${BLUE}==>${RESET} Populating search and proximity indices..."
	@$(PYTHON) manage.py populate_search_data
	@$(PYTHON) manage.py populate_proximity_locations

.PHONY: backfill-ratings
backfill-ratings: ## Recalculate and backfill cached place ratings
	@$(PYTHON) manage.py backfill_cached_ratings

##@ 🐳 Docker Compose Operations

.PHONY: docker-up
docker-up: ## Start all Docker services in background (web, db, telegram)
	@echo -e "${GREEN}==>${RESET} Starting Docker services..."
	@docker-compose up -d

.PHONY: docker-down
docker-down: ## Stop and remove all Docker containers
	@echo -e "${YELLOW}==>${RESET} Stopping Docker services..."
	@docker-compose down

.PHONY: docker-build
docker-build: ## Rebuild and restart Docker containers with uv
	@echo -e "${BLUE}==>${RESET} Building Docker containers with uv..."
	@docker-compose up -d --build

.PHONY: docker-logs
docker-logs: ## Follow live logs from the web service
	@docker-compose logs -f web

.PHONY: docker-shell
docker-shell: ## Open interactive bash shell inside web container
	@docker-compose exec web bash

.PHONY: docker-migrate
docker-migrate: ## Run database migrations inside Docker
	@docker-compose exec web python manage.py migrate

.PHONY: docker-test
docker-test: ## Run automated tests inside Docker (usage: make docker-test [APP=places])
	@docker-compose exec web python manage.py test $(APP)

.PHONY: docker-seed
docker-seed: ## Seed test places inside Docker
	@docker-compose exec web python manage.py create_test_data

##@ 🧪 Testing & Code Quality

.PHONY: test
test: ## Run the full automated test suite
	@echo -e "${BLUE}==>${RESET} Running automated tests..."
	@$(PYTHON) manage.py test

.PHONY: test-app
test-app: ## Run tests for a specific app (usage: make test-app APP=places)
	@if [ -z "$(APP)" ]; then echo -e "${YELLOW}Usage: make test-app APP=<app_name>${RESET}"; exit 1; fi
	@$(PYTHON) manage.py test $(APP)

.PHONY: coverage
coverage: ## Run test suite with terminal coverage report
	@echo -e "${BLUE}==>${RESET} Computing test coverage..."
	@$(RUN) coverage run --source='.' manage.py test
	@$(RUN) coverage report -m

.PHONY: coverage-html
coverage-html: ## Generate HTML test coverage report in htmlcov/
	@echo -e "${BLUE}==>${RESET} Generating HTML coverage report..."
	@$(RUN) coverage run --source='.' manage.py test
	@$(RUN) coverage html
	@echo -e "${GREEN}==>${RESET} Report available at htmlcov/index.html"

.PHONY: lint
lint: ## Check codebase for linting issues using Ruff
	@echo -e "${BLUE}==>${RESET} Running Ruff linter..."
	@$(RUN) ruff check .

.PHONY: format
format: ## Auto-format code using Ruff (usage: make format [PATH=app_name/])
	@echo -e "${BLUE}==>${RESET} Formatting code with Ruff..."
	@$(RUN) ruff format $(or $(PATH),.)

##@ 🌐 Translations & Localization (i18n)

.PHONY: messages
messages: ## Extract translatable strings for Korean (ko) and Uzbek (uz)
	@echo -e "${BLUE}==>${RESET} Extracting translation messages..."
	@$(PYTHON) manage.py makemessages -l ko
	@$(PYTHON) manage.py makemessages -l uz

.PHONY: compilemessages
compilemessages: ## Compile .po translation catalogs into binary .mo files
	@echo -e "${BLUE}==>${RESET} Compiling translation catalogs..."
	@$(PYTHON) manage.py compilemessages

.PHONY: translation-status
translation-status: ## Report translation progress across languages
	@$(PYTHON) manage.py translation_status

.PHONY: translation-check
translation-check: ## Check translation consistency between EN, KO, and UZ
	@$(PYTHON) manage.py check_translation_consistency

.PHONY: validate-translations
validate-translations: ## Validate syntax and completeness of translation files
	@$(PYTHON) manage.py validate_translations

##@ 📊 Monitoring, Telemetry & Backups

.PHONY: backup
backup: ## Run database backup (only if database changed)
	@$(PYTHON) manage.py backup_database

.PHONY: backup-force
backup-force: ## Force immediate database backup and send to Telegram
	@$(PYTHON) manage.py backup_database --force

.PHONY: backup-local
backup-local: ## Create local database backup without sending to Telegram
	@$(PYTHON) manage.py backup_database --local-only

.PHONY: metrics
metrics: ## Aggregate hourly and daily system monitoring metrics
	@$(PYTHON) manage.py aggregate_metrics

.PHONY: check-alerts
check-alerts: ## Evaluate alert thresholds and dispatch notifications
	@$(PYTHON) manage.py check_alerts

.PHONY: health
health: ## Check overall monitoring system health
	@$(PYTHON) manage.py check_monitoring_health

.PHONY: digest
digest: ## Dispatch daily administrative summary report
	@$(PYTHON) manage.py send_daily_digest

.PHONY: test-telegram
test-telegram: ## Verify Telegram Bot API connectivity
	@$(PYTHON) manage.py test_telegram

.PHONY: test-email
test-email: ## Probe Brevo SMTP/REST ports and test email delivery
	@$(PYTHON) manage.py test_email --check-ports

.PHONY: test-watermark
test-watermark: ## Test Pillow image watermarking pipeline
	@$(PYTHON) manage.py test_watermark static/images/logo-square.png

##@ 🧹 Maintenance & Housekeeping

.PHONY: collectstatic
collectstatic: ## Collect static files into staticfiles/ directory
	@echo -e "${BLUE}==>${RESET} Collecting static assets..."
	@$(PYTHON) manage.py collectstatic --noinput

.PHONY: clean
clean: ## Remove python bytecode, test artifacts, and caches
	@echo -e "${YELLOW}==>${RESET} Cleaning cache files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@rm -rf .pytest_cache .coverage htmlcov .ruff_cache 2>/dev/null || true
	@echo -e "${GREEN}==>${RESET} Clean complete."

.PHONY: tail-logs
tail-logs: ## Follow live application log output
	@tail -f logs/django.log

.PHONY: tail-errors
tail-errors: ## Follow live error log output
	@tail -f logs/django_errors.log
