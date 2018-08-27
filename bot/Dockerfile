FROM python:3.6-alpine

RUN adduser -D scrumbot

WORKDIR /home/scrumbot

RUN apk --update add --virtual build-dependencies gcc musl-dev

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

RUN apk del build-dependencies gcc musl-dev

COPY bot.py client.py run.py ./

ENV DATA_DIR=/data


RUN chown -R scrumbot:scrumbot ./
USER scrumbot

ENTRYPOINT ["python", "run.py"]