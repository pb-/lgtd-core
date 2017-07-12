FROM python:2

RUN pip install git+git://github.com/pb-/lgtd-core
RUN mkdir -p /lgtd/data

COPY server.crt server.key /lgtd/

EXPOSE 9002

WORKDIR /lgtd
CMD lgtd_syncd -S data server.crt server.key
