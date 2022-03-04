# Scheduler

## Purpose

The scheduler is responsible for scheduling the execution of tasks.

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
$ tree -L 1 --dirsfirst

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
