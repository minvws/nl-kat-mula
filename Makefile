SHELL := bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.DELETE_ON_ERROR:
MAKEFLAGS += --warn-undefined-variables
MAKEFLAGS += --no-builtin-rules
# Makefile Reference: https://tech.davis-hansson.com/p/make/

.PHONY: help mypy check black req done lint env

# use HIDE to run commands invisibly, unless VERBOSE defined
HIDE:=$(if $(VERBOSE),,@)

BLACKFLAGS= -l 120 --exclude ""
BYTES_VERSION= v0.6.0

# Export cmd line args:
export VERBOSE
export m
export build

# Export Docker buildkit options
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1


##
##|------------------------------------------------------------------------|
##			Help
##|------------------------------------------------------------------------|
help: ## Show this help.
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/ ##/			/' | sed -e 's/##//'

##
##|------------------------------------------------------------------------|
##			Development
##|------------------------------------------------------------------------|

check: ## Check the code style using black and mypy.
	make black
	make mypy
	make pylint
	make rcheck

mypy: ## Check code style using mypy.
	pipenv run mypy --install-types --non-interactive --ignore-missing-imports . --implicit-reexport

black: ## Check code style with black.
	pipenv run black --check --diff $(BLACKFLAGS) .

pylint: ## Rate the code with pylint.
	pipenv run pylint scheduler | grep rated

rcheck: ## Check if the requirements.txt files match the pipenv lock output.
	$(HIDE) pipenv lock -r 2>/dev/null |
		diff -q -I "nl-rt-tim-abang-" requirements.txt - ||
		(echo "requirements.txt out of date! Run 'make req' to fix this" && exit 1)
	$(HIDE) pipenv lock --dev -r 2>/dev/null |
		diff -q -I "nl-rt-tim-abang-" requirements-dev.txt - ||
		(echo "requirements-dev.txt out of date! Run 'make req' to fix this" && exit 1)
	$(HIDE) echo "Requirement files up to date."

lint: ## Format the code using black.
	pipenv run black $(BLACKFLAGS) .

req: ## Update the requirements.txt file for backward compatibility in the venv builds.
	pipenv lock -r > requirements.txt
	echo "git+ssh://git@github.com/minvws/nl-rt-tim-abang-bytes@$(BYTES_VERSION)" >> requirements.txt
	pipenv lock --dev -r > requirements-dev.txt

done: ## Prepare for a commit.
	make lint
	make check
	make req
	make test

sql: ## Generate raw sql for the migrations.
	docker-compose exec scheduler \
		alembic \
		--config /app/scheduler/alembic.ini \
		upgrade $(rev1):$(rev2) --sql

migration: ## Create migration.
ifeq ($(m),)
	$(HIDE) (echo "Specify a message with m={message} and a rev-id with revid={revid} (e.g. 0001 etc.)"; exit 1)
else ifeq ($(revid),)
	$(HIDE) (echo "Specify a message with m={message} and a rev-id with revid={revid} (e.g. 0001 etc.)"; exit 1)
else
	docker-compose \
		exec \
		scheduler \
		alembic \
		--config /app/scheduler/alembic.ini \
		revision \
		--autogenerate \
		-m "$(m)" \
		--rev-id "$(revid)"
endif

migrate: ## Run migrations using alembic.
	docker-compose exec scheduler \
		alembic \
		--config /app/scheduler/alembic.ini \
		upgrade head

##
##|------------------------------------------------------------------------|
##			Tests
##|------------------------------------------------------------------------|

utest: ## Run the unit tests.
ifneq ($(build),)
	docker-compose -f base.yml -f .ci/docker-compose.yml build mula_unit
endif
	docker-compose -f base.yml  -f .ci/docker-compose.yml run --rm mula_unit; docker-compose -f base.yml  -f .ci/docker-compose.yml down

itest: ## Run the integration tests.
ifneq ($(build),)
	docker-compose -f base.yml -f .ci/docker-compose.yml build mula_integration
endif
	docker-compose -f base.yml  -f .ci/docker-compose.yml run --rm mula_integration; docker-compose -f base.yml  -f .ci/docker-compose.yml down

test: ## Run all tests.
	make utest
	make itest
