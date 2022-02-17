FROM python:3.8

ARG PIP_PACKAGES=requirements.txt

WORKDIR /app/scheduler

COPY ["requirements.txt", "${PIP_PACKAGES}", "logging.json", "./"]
RUN pip install -r ${PIP_PACKAGES}

COPY scheduler/ /app/scheduler/

CMD ["python", "-m", "scheduler"]
