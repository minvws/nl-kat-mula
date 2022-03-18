# Scheduler

## Purpose

The scheduler is responsible for scheduling the execution of tasks. The
execution of those tasks are being prioritized / scored by a ranker. The
tasks are then pushed onto a priority queue. A dispatcher pop's tasks of
the queue and send those tasks to a worker to be picked up.

Within the project of KAT, the scheduler is tasked with scheduling boefje and
normalizer tasks.

## Architecture

See [design](docs/design.md) document for the architecture.

### Stack

| Name           | Version  |
|----------------|----------|
| Python         | 3.8      |


### External services

**TODO**

### Project structure

```
$ tree -L 3 --dirsfirst
.
├── docs/
├── scheduler/                      # scheduler python module
│   ├── config                      # application settings configuration
│   ├── connectors                  # external services connectors
│   │   ├── listeners               # channel/socket listeners
│   │   ├── services                # api connectors
│   │   └── __init__.py
│   ├── context/                    # shared application context
│   ├── datastore/                  # datastore connections
│   ├── models/                     # internal model definitions
│   ├── queue/                      # priority queue
│   ├── ranker/                     # priority/score calculations
│   ├── server/                     # scheduler api interface
│   ├── dispatcher.py               # tasks dispatcher
│   ├── __init__.py
│   ├── __main__.py
│   ├── scheduler.py                # scheduler app definition
│   └── thread.py                   # thread runner implementation support
└─── tests/
    ├── factories/
    ├── integration/
    ├── simulation/
    ├── unit/
    └── __init__.py

```

## Running / Developing

### Prerequisites

By the use of environment variables we load in the configuration of the 
scheduler. 

### Running

```
$ docker-compose up --build -d scheduler
```

## Testing

```
$ make utest
```
