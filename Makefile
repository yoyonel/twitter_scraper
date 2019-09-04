# https://www.gnu.org/software/make/manual/html_node/Phony-Targets.html
.PHONY: clean clean-build clean-pyc help
# https://www.gnu.org/software/make/manual/html_node/Special-Variables.html
.DEFAULT_GOAL := help

ORGANIZATION_NAME?=yoyonel
PROJECT_NAME?=twitter_scraper
#
PACKAGE_NAME=$(shell python setup.py --name)
PACKAGE_FULLNAME=$(shell python setup.py --fullname)
PACKAGE_VERSION:=$(shell python setup.py --version | tr + _)
#
DOCKER_TAG?=yoyonel/$(PROJECT_NAME):${PACKAGE_VERSION}
#
PYPI_SERVER?=
PYPI_REGISTER?=
# https://stackoverflow.com/questions/2019989/how-to-assign-the-output-of-a-command-to-a-makefile-variable
PYPI_SERVER_HOST=$(shell echo $(PYPI_SERVER) | sed -e "s/[^/]*\/\/\([^@]*@\)\?\([^:/]*\).*/\2/")
PYTEST_OPTIONS?=-v
#
TOX_DIR?=${HOME}/.tox/$(ORGANIZATION_NAME)/$(PROJECT_NAME)
#
SDIST_PACKAGE=dist/${shell python setup.py --fullname}.tar.gz
SOURCES=$(shell find src/ -type f -name '*.py') setup.py MANIFEST.in
PROTOS=$(shell find src/ -type f -name '*.proto')

MONGODB_USER?=user
MONGODB_PASSWORD?=password

# https://github.com/AnyBlok/anyblok-book-examples/blob/III-06_polymorphism/Makefile
define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT
help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

all: docker

build_proto_modules: ${PROTOS}
	@echo "Building proto modules ..."
	@python setup.py build_proto_modules

${SDIST_PACKAGE}: ${SOURCES}
	@echo "Building python project..."
	@python setup.py sdist

docker: ${SDIST_PACKAGE} docker/Dockerfile
	@echo PYPI_SERVER: $(PYPI_SERVER)
	@docker build \
		--build-arg PYPI_SERVER=$(PYPI_SERVER) \
		-t $(DOCKER_TAG) \
		-f docker/Dockerfile \
		.

docker-run:
	@docker run --rm -it ${DOCKER_RUN_OPTIONS} $(DOCKER_TAG)

docker-run-shell:
	@docker run --rm -it ${DOCKER_RUN_OPTIONS} --entrypoint sh $(DOCKER_TAG)

pypi-register:
	python setup.py register -r ${PYPI_REGISTER}
	
pypi-upload: pypi-register
	python setup.py sdist upload -r ${PYPI_REGISTER}

pip-install:
	@pip install \
		-r requirements_dev.txt \
		--trusted-host $(PYPI_SERVER_HOST) \
		--extra-index-url $(PYPI_SERVER) \
		--upgrade

pipenv-lock:
	pipenv lock

pipenv-install_with_lock: pipenv-lock
	pipenv install --ignore-pipfile

pytest:
	pytest ${PYTEST_OPTIONS}

tox:
	# http://ahmetdal.org/jenkins-tox-shebang-problem/
	tox --workdir ${TOX_DIR}

dev.up: docker	## launch docker-compose project (MongoDB, RPC services) [dev mode]
	DOCKER_TAG=${DOCKER_TAG} \
		docker-compose -f docker/docker-compose.build.yml up

up: docker	## launch docker-compose project (MongoDB, RPC services)
	DOCKER_TAG=${DOCKER_TAG} \
		docker-compose \
			-f docker/docker-compose.yml \
			up

up_mongodb:	## launch MongoDB service from docker-compose project
	# https://stackoverflow.com/questions/30233105/docker-compose-up-for-only-certain-containers
	DOCKER_TAG=${DOCKER_TAG} \
		docker-compose \
			-f docker/docker-compose.yml \
			up ${DOCKERCOMPOSE_UP_OPTIONS} mongodb

up_mongodb_detach:	## launch MongoDB service from docker-compose project (in detach mode)
	DOCKERCOMPOSE_UP_OPTIONS="--detach" make up_mongodb

mongo_shell:
	mongo \
		--username user \
		--password password \
		127.0.0.1:27017/$(PROJECT_NAME)

mongo_export:
	mongoexport \
		--db $(PROJECT_NAME) \
		--collection tweets \
		--username user \
		--password password \
		--jsonArray \
		--pretty \
		--out tests/fixtures/mongodb/tweets.json

mongo_drop:
	mongo \
		127.0.0.1:27017/$(PROJECT_NAME) \
		-u user -p password \
		--eval "db.tweets.drop()"

clean: clean-build clean-pyc ## remove all build, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
