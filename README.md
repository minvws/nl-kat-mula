# Scheduler

## Purpose

The scheduler is responsible for scheduling the execution of tasks. The
execution of those tasks are being prioritized / scored by a ranker. The
tasks are then pushed onto a priority queue. A dispatcher pop's tasks of
the queue and send those tasks to a worker to be picked up.

Within the project of KAT, the scheduler is tasked with scheduling boefje tasks.

## Architecture

See [design](docs/design.md) document for the architecture.

### Stack, packages and libraries

| Name           | Version  | Description                                       |
|----------------|----------|---------------------------------------------------|
| Python         | 3.8      |                                                   |
| FastAPI        | 0.73.0   | Used for api server                               |
| Celery         | 5.2.3    | Used for even listening, and dispatching of tasks |

### External services

The scheduler interfaces with the following services:

| Service | Usage |
|---------|-------|
| [Octopoes](https://github.com/minvws/nl-rt-tim-abang-octopoes) | Retrieving random OOI's of organizations |
| [Katalogus](https://github.com/minvws/nl-rt-tim-abang-boefjes/tree/develop/katalogus) | Used for referencing available boefjes, and organizations |
| [Bytes](https://github.com/minvws/nl-rt-tim-abang-bytes) | Retrieve last run boefje for organization and OOI |
| [Boefjes](https://github.com/minvws/nl-rt-tim-abang-boefjes) | Sending boefje task via Celery |
| [RabbitMQ]() | Used for retrieving scan profile changes |

### Project structure

```
$ tree -L 3 --dirsfirst
.
├── docs/                           # additional documentation
├── scheduler/                      # scheduler python module
│   ├── config                      # application settings configuration
│   ├── connectors                  # external services connectors
│   │   ├── listeners               # channel/socket listeners
│   │   ├── services                # api connectors
│   │   └── __init__.py
│   ├── context/                    # shared application context
│   ├── dispatchers/                # queue task dispatcher
│   ├── models/                     # internal model definitions
│   ├── queues/                     # priority queue
│   ├── rankers/                    # priority/score calculations
│   ├── schedulers/                 # scheduler api interface
│   ├── server/                     # scheduler api interface
│   ├── utils/                      # common utility functions
│   ├── __init__.py
│   ├── __main__.py
│   ├── app.py                      # kat scheduler app implementation
│   └── version.py                  # version information
└─── tests/
    ├── factories/
    ├── integration/
    ├── simulation/
    ├── unit/
    └── __init__.py
```

## Running / Developing

Typically the scheduler will be run from the overarching
[nl-rt-tim-abang](https://github.com/minvws/nl-rt-tim-abang) project. When
you want to run and the scheduler individually you can use the following setup.
We are using docker to setup our development environment, but you are free
to use whatever you want.

### Prerequisites

By the use of environment variables we load in the configuration of the 
scheduler. Look at the [.env-dist](.env-dist) file for the application
configuration settings.

### Running

```
# Build and run the scheduler in the background
$ docker-compose up --build -d scheduler
```

## Testing

```
# Run integration tests
$ make itest

# Run unit tests
$ make utest

# Individually test a file
$ make file=test_file.py utest

# Individually test a function
$ make file=test_file.py function=-k test_function utest
```
