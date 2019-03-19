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

image:
	docker build -t lgtd .
.PHONY: image

publish:
	docker tag lgtd pbgh/lgtd
	docker push pbgh/lgtd
.PHONY: publish
