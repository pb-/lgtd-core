FROM python:2-alpine

ADD . /code
RUN pip install /code

WORKDIR /lgtd
CMD lgtd_syncd -S data server.crt server.key
