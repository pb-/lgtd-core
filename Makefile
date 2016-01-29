all: check isort test

isort:
	isort --recursive lgtd

check:
	flake8 lgtd

test:
	py.test lgtd
