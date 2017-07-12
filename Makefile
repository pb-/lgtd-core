all: check sort test

sort:
	isort --check-only --recursive lgtd

check:
	flake8 lgtd

test:
	py.test lgtd

build:
	docker build -t lgtd .

run:
	docker run -d --restart always -v /var/lib/lgtd:/lgtd -p 9002:9002 lgtd
