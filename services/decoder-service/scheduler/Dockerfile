FROM python:3.6.10-buster

ENV CONTAINER=1

COPY . /app
WORKDIR /app

RUN pip3 install -r requirements.txt

ENTRYPOINT ["python3", "-u", "server.py"]
