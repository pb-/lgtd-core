FROM python:2

RUN pip install git+git://github.com/pb-/lgtd-core

EXPOSE 9002

WORKDIR /lgtd
CMD lgtd_syncd -S data server.crt server.key
