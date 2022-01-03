# Proposal: design scheduler

## Purpose

The *scheduler* maintains a priority queue for discovery tasks to be performed
by the ... workers (*boefjes*). The scheduler is tasked with maintaining and
updating the priority queue with jobs that can be picked up by the workers.

A priority queue is used, in as such, that it allows us to determine what jobs
(TODO: OOI's?) should be checked first, or more regularly. Because of the use
of a priority queue we can differentiate between jobs that are to be executed
first. E.g. job's created by the user get precedence over jobs that are created
by the internal rescheduling processes within the scheduler.

Calculations in order to determine the priority of a job is performed by logic
that can/will leverage information from multiple sources, including but not
limited to ... (TODO: expand on this, what, and how)

### Requirements

**Input**

* Expose API for new findings to be posted for scheduling

* Listen on channels (TODO: determine what channels) for new findings to be
  posted for scheduling

**Scheduling and Rescheduling**

* Scheduling of new findings

* Process of rescheduling of tasks that already have been completed

**Priority Queue**

* Finite (configurable) number of items in the priority queue

* Recreate state of priority queue from persistent storage, priority queue
  is maintained in memory.

**Calculation**

* Should be able to implement different calculation strategies for determining
  the priority of a task, and maintaining order. At least it should be able to
  easily be extended to include more strategies, or other strategies.

* Take into account organization's scan profile level

**Output**

* Expose API for tasks to be popped of the priority queue

* Accesses multiple 'external' services to determine

## Architecture

* Continual process that updates and maintains the priority queue

* TODO: internal state

## Design decisions / Open questions

* Now boefjes pop tasks from the centralized job queue (rabbitmq `boefjes`),
  the intention is to replace this queue with the priority queue of the
  scheduler.

* Do we maintain the priority queue within the scheduler or do we leverage
  other services (e.g. redis) to maintain the queue?

  Suggested is that we keep the priority queue within the scheduler in memory.

* What types of channels does the scheduler maintain to receive/input new tasks
  to be pushed onto the priority queue? E.g. and API to post jobs to the
  scheduler, a listener on to a message queue channel, and active process that
  looks for interesting findings to be posted to the scheduler? A combination
  of these, or all of them?

* How do we keep track of the status of job, meaning do we need to poll to
  check if it has been processed by the workers, or do we wait for
  confirmation?

## Scratchpad

* Will the scheduler also schedule normalization jobs?

  This is because it seems that the scheduler's current function is to do
  just that.

* investigate boefjes cron jobs in rocky (done every minute)

  schedule new boefjes > start job
    > fill master list
      > get ooi's from queue `create_events`, from that get org, use org
        to create scan profile
    > get all scan profiles that are new, exclude L0
    > schedule boefjes for scan profiles
      > schedule boefje
        > run boefje pipeline
          > check indemnification
          > run boefje
          > create boefje
      > set scan profile attr new to false

* When is a scan profile new? When created how is it picked up by a boefje?
  Why are we checking for new scan profiles in the cron job, shouldn't those
  already be picked up by the boefjes?

  ScanProfile is a model in app `/tools`

* Does the scheduler need to know what boefje to use?

  Does not seem likely if we create a priority queue from which boefjes can
  pop off tasks.

* What services create scans for boefjes at the moment and how are they created?

  - creating a scan in rocky
    > `views.scans.scan_create()`
      > `boefjes.boefjes.run_boefje`
        > `create_job_from_boefje`
          > Creates `Job` model
        > `run_boefje_job`
          > sends task on queue `boefjes`
        > `set_scan_profiles`

  - octopoes finds objects (TODO: finds how? what process? who listens to this
    channel? > The cron job in rocky) and adds them to the queue `create_events`

    Posts create events on `create_events` queue. Located in`api.py`,
    `dispatch_create_events`

  - cron job within rocky, runs every minute, checks in `create_events` queue
    creates tasks for boefjes

* What is the flow in rocky when starting a scan?

  - creating a scan in rocky
    > `views.scans.scan_create()`
      > `boefjes.boefjes.run_boefje`
        > `create_job_from_boefje`
          > Creates `Job` model
        > `run_boefje_job`
          > sends task on queue `boefjes`
        > `set_scan_profiles`

  `PerformScanForm`, creates a `ScanProfile`

  - Listed as "tasks" list view at `/tasks` `views/tasks.py`, get the list
    from flower `tasks.handle_boefje` finds the associated `Job` models,
    (NOTE: queue is not specified btw)

    tasks are pushed on the `tasks.handle_boefje` in `boefje/boefje.py`

```python
app.send_task(
"tasks.handle_boefje", (job_meta,), queue="boefjes", task_id=job_meta.id
)
```

* How does octopoes find new objects?

  New found objects are pushed on the `create_events` queue.


* When and by what is `POST /{client}` used, in octopoes?
