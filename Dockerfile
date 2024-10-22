FROM python:3.11.6
RUN apt-get update && apt-get install -y -q --no-install-recommends \
    ntpdate
RUN mkdir ./humanfirst-module
COPY . /humanfirst-module
WORKDIR /humanfirst-module
RUN python -m pip install --upgrade pip
RUN python -m pip install -r requirements.txt