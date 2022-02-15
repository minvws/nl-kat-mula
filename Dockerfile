FROM python:3.8

WORKDIR /app/scheduler

COPY ["requirements.txt", "logging.json", "./"]
RUN pip install -r requirements.txt

COPY scheduler/ /app/scheduler/

CMD ["python", "-m", "scheduler"]
