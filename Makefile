all: check sort test

sort:
	isort --check-only --recursive lgtd
.PHONY: sort

check:
	flake8 lgtd
.PHONY: check

test:
	py.test lgtd
.PHONY: test

build:
	docker-compose build
.PHONY: build

up:
	docker-compose up
.PHONY: up

upd:
	docker-compose up -d
.PHONY: upd
