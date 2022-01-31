FROM python:3.8

WORKDIR /app

COPY ["requirements.txt", "logging.json", "./"]
RUN pip install -r requirements.txt

COPY scheduler/ scheduler/

CMD ["python", "-m", "scheduler"]
