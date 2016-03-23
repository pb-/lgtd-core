all: check sort test

sort:
	isort --check-only --recursive lgtd

check:
	flake8 lgtd

test:
	py.test lgtd
