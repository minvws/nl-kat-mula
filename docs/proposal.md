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
limited to octopoes, bytes, ... (TODO: expand on this, what, and how)

### Requirements

**Input**

Describes how we get initial state of the scheduler system, and how we add,
update, delete objects.

* The input of new jobs can be done by 2 processes:

  1. Cold start; in order to make sure that we are current and we have
     a correct representation of the state of their respective systems, we need
     to have a process that gathers all the data and persist them in the
     internal state of the scheduler. This can then be run as a sanity check,
     or as a part of the initial start of the scheduler.

     TODO: other name, since it will be executed to make sure the internal
     state is correct.

  2. Event subscription; the scheduler will listen to add, delete, update
     events to update the internal state of the scheduler, as such update
     the priority/score of an object.

  For both of the boefjes, and normalizer jobs these two mechanisms need to be
  supported.

  **Boefjes**

  1. Reference octopoes in order to get new OOI's

  2. Subscribe to event channel of Octopoes

  NOTE: workers are now directly called by rocky to execute a job, in the new
  setup this will need to go through the scheduler first and then be executed
  by the workers with the highest priority. Additionally, the cron jobs that
  are now present in rocky that listen to the message queue `create_events`
  will be implemented in the scheduler.

  **Normalizers**

  1. **TODO**

  2. **TODO**

**Scheduling and Rescheduling**

* Scheduling of objects onto the priority queue

  Suggested is to take a random set of objects and schedule them onto the
  priority queue. However, that process needs to make sure that newly issued
  scan from the webapp takes precedence and are pushed onto the queue.

* Process of rescheduling of tasks that already have been completed

  Based on the change of findings (and additional scoring features) for a
  particular object, the score/priority for the object will be updated
  resulting in objects being rescheduled more/less often. 

**Priority Queue**

* Finite (configurable) number of items in the priority queue

* Priority queue is implemented as a heap and maintained in memory 

* Recreate state of priority queue from persistent storage

**Calculation**

* Should be able to implement different calculation strategies for determining
  the priority of a task, and maintaining order. At least it should be able to
  easily be extended to include more strategies, or other strategies.

* Take into account organization's scan profile level

* Accesses multiple 'external' services to determine the priority of a task

**Output**

* Expose API for tasks to be popped of the priority queue, initially as a
  RESTful API. Should be extensible to support other API protocols when needed.

* A worker should be able to ask for a specific task for that worker to be
  popped of the queue. It should have no knowledge of jobs that are are
  scheduled for other workers.

## Architecture

Following describes main processes of the scheduler:

* `ColdStart` - process that gathers all object and persist them in the
  internal state (the `frontier`) of the scheduler ready for scheduling.

* `Listener` - process that listens on a channel for object changes 
  (at the moment this is `create_events`), and persists those objects into
  the database table `frontier`.

* `CalculateScore` - process that calculates the score of an object based on
  the change in findings and other factors.

* `GetObjectsFromFrontier` process, takes objects from the `frontier` table and
  schedules them for execution. This pushes objects onto the priority queue
  `AddToQueue`.

* `API` allows worker to pop off jobs from the priority queue, filtered by
   their worker type.

## Design decisions / Open questions

* Boefjes scan jobs are now being called directly through the rabbitmq
  `boefjes` channel by rocky, leveraging celery, the intention is to replace
  this with by the scheduler.

* Rocky cron jobs that are checking the `create_events` channel need to be
  replaced by the scheduler.

* Do we maintain the priority queue within the scheduler or do we leverage
  other services (e.g. redis) to maintain the queue?

  Suggested is that we keep the priority queue within the scheduler in memory.
  We can also program it generalized enough that other backends can be used
  or swapped with minimal effort. At this moment there would be too much
  overhead on using external services, and can be implemented more easily
  within the scheduler service and allows us more flexibility .

* What types of channels does the scheduler maintain to receive/input new tasks
  to be pushed onto the priority queue? E.g. and API to post jobs to the
  scheduler, a listener on to a message queue channel, and active process that
  looks for interesting findings to be posted to the scheduler? A combination
  of these, or all of them?

  Suggested is to have a event stream channel(s) to which the scheduler
  subscribes to. Significant event types are:

  **Boefjes**:

  * Add OOI events by boefjes
  * Indemnification events
  * Scan events

  TODO: incomplete, what normalizer events?

* How do we keep track of the status of job, meaning do we need to poll to
  check if it has been processed by the workers, or do we wait for
  confirmation, will this be posted on a event channel?

  When a scan job has been completed is known by `bytes`. Suggested is to
  check outstanding jobs that have been done in a specific time frame, when
  the job failed it should get a higher priority. (TODO: is this correct?)

* Do we want a mechanism to override the priority of a task?

  Suggested is to solve this with deduplication and save highest priority
  (TODO: unsure)

* Can we use the same data structure that are used for the boefjes in the
  `test/examples/` directory, for the objects that are on the priority queue?

  Suggested is to use `JobMeta` model, the object that is popped off the
  queue would be json serializable and should contain:

  * the input OOI
  * boefje container image
  * environment settings

* For the queue `create_events` is there a offset available?

  See coldstart need to reference octopoes, and that is your offset

* Decide what the priority score for object on the priority queue should be.
  E.g. the scan level?

  Priority is based on delta of change of an OOI

* For call to calculate the `CalculateScore`, do we want to let the scheduler
  listen to a channel to check when a job is finished, and then update the
  object? Or do we want to expose an API (e.g. rpc) to update it, so that the
  responsibility lies with the workers?

  The scheduler will listen to an event stream (or additionally get info
  from `bytes` when a scan job is completed) update the internal state of an
  object, and update the priority of the object.

* What external services are available and do we want to use in order to 
  calculate the `CalculateScore`?

  * Bytes; historical information of when a boefje has run, on a specific OOI
  * Katalogus; what boefje can be used with what OOI (TODO: permutation set?)
  * Pichu; indemnification set
  * Octopoes; tells what findings there are found with every OOI

## Scratchpad

* Will the scheduler also schedule normalization jobs?

  This because, it seems that the scheduler's current function is to do
  just that. Yes, this will be a separate priority and needs different
  information.

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
  pop off tasks. The scheduler does not specifically need to know this,
  but will get this information from other services.

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

  The graph changes, that has repercussions on the graph. It could mean that
  nodes need to be removed. The scheduler needs to subscribe to an event
  stream to listen to these changes and update the priority queue as a
  result.

* When and by what is `POST /{client}` used, in octopoes?

  used as module in other services as:
  `octopoes.connector.octopoes.OctopoesAPIConnector` using the `save()` method

  `def save(self, report: CombinationReport) -> List[Change]:`

   `CombinationReport`: Serializable object to send a Combination to Octopoes API
   `Combination`: XTDB object to store a Combination output

* Do we have centralized metrics? Are we keeping track of metrics for boefjes
  for instance? Do we want to track metrics like the size of the queue?

  Future

* Do we have centralized logging? Log-based metrics.

  Future
