FROM python:2-alpine

ADD . /code
RUN pip install /code

EXPOSE 9002/tcp
VOLUME ["/data"]

WORKDIR /
CMD lgtd_syncd -S data
