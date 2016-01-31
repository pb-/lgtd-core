all: check sort test

sort:
	isort --recursive lgtd

check:
	flake8 lgtd

test:
	py.test lgtd
