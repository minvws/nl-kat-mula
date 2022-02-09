FROM python:3.8

WORKDIR /app/scheduler

# Install the pipenv package in pip.
RUN pip install pipenv

# Copy over our Pipfiles so we can install our env
COPY nl-rt-tim-abang-mula/Pipfile ./
COPY nl-rt-tim-abang-mula/Pipfile.lock ./

# Install dependencies
RUN pipenv install --dev --deploy --verbose

COPY nl-rt-tim-abang-mula/ .
