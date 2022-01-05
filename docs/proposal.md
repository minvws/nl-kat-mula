# Proposal: design scheduler

## Purpose

The *scheduler* maintains a priority queue for discovery tasks to be performed
by the workers (*boefjes* and *normalizers*). The scheduler is tasked with
maintaining and updating the priority queue with jobs that can be picked up by
the workers.

A priority queue is used, in as such, that it allows us to determine what jobs
should be checked first, or more regularly. Because of the use of a priority
queue we can differentiate between jobs that are to be executed first. E.g.
job's created by the user get precedence over jobs that are created by the
internal rescheduling processes within the scheduler. (TODO: correct
assumption?)

Calculations in order to determine the priority of a job is performed by logic
that can/will leverage information from multiple sources, including but not
limited to ... (TODO: expand on this, what, and how)

### Requirements

**Input**

* Expose API for new findings to be posted for scheduling

  TODO: determine whether or not this is necessary, since we have a channel
  `create_events` that is used to post new events to the scheduler.

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

* Accesses multiple 'external' services to determine the priority of a task

**Output**

* Expose API for tasks to be popped of the priority queue

## Architecture

* `listener` process that listens on a channel for objects (TODO: right term?)
  (at the moment this is `create_events`), and persists those objects into
  the database table `frontier`.

* `NextCheck` process or call, for finished jobs it calculates the next time
  the job should be checked. For new jobs that haven't been checked the
  `NextCheck` will be set to the current time.

* `GetFromFrontier` process, takes objects from the `frontier` table and
  schedules them for execution. This pushes objects onto the priority queue.
  `AddToQueue`.

## Design decisions / Open questions

* Now boefjes pop tasks from the centralized job queue (rabbitmq `boefjes`),
  the intention is to replace this queue with the priority queue of the
  scheduler.

* Do we maintain the priority queue within the scheduler or do we leverage
  other services (e.g. redis) to maintain the queue?

  Suggested is that we keep the priority queue within the scheduler in memory.

  We can also program it generalized enough that other backends can be used
  of swapped with minimal effort.

* What types of channels does the scheduler maintain to receive/input new tasks
  to be pushed onto the priority queue? E.g. and API to post jobs to the
  scheduler, a listener on to a message queue channel, and active process that
  looks for interesting findings to be posted to the scheduler? A combination
  of these, or all of them?

* How do we keep track of the status of job, meaning do we need to poll to
  check if it has been processed by the workers, or do we wait for
  confirmation?

* Do we want a mechanism to override the priority of a task?

* Can we use the same data structure that are used for the boefjes in the
  `test/examples/` directory, for the objects that are on the priority queue?

* For the queue `create_events` is there a offset available?

* Decide what the priority score for object on the priority queue should be.
  E.g. the scan level?

* For call to calculate the `NextCheck`, do we want to let the scheduler listen
  to a channel to check when a job is finished, and then update the object?
  Or do we want to expose an API (e.g. rpc) to update it, so that the
  responsibility lies with the workers?

* What external services are available and do we want to use in order to 
  calculate the `NextCheck`?

## Scratchpad

* Will the scheduler also schedule normalization jobs?

  This because, it seems that the scheduler's current function is to do
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

    New found objects (TODO: is this true, are these new found objects? when
    a scan job is created by rocky, the newly created object in octopoes is
    picked up and posted on the `create_events` queue) are pushed on the
    `create_events` queue, these are created by the normalizers.

    `octopoes/api.py`
    `post_combination_report`
      > `dispatch_create_events`

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

* What is a combination report?

  results in a diff

* When and by what is `POST /{client}` used, in octopoes?

  used as module in other services as:
  `octopoes.connector.octopoes.OctopoesAPIConnector` using the `save()` method

  `def save(self, report: CombinationReport) -> List[Change]:`

   `CombinationReport`: Serializable object to send a Combination to Octopoes API
   `Combination`: XTDB object to store a Combination output

* Do we have centralized metrics? Are we keeping track of metrics for boefjes
  for instance? Do we want to track metrics like the size of the queue?

* Do we have centralized logging? Log-based metrics.
