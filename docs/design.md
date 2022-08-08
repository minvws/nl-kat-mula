# Design scheduler

## Purpose

The *scheduler* is tasked with populating and maintaining a priority queue of
items that are ranked, and can be popped off (through api calls), or dispatched.
The scheduler is designed to be extensible, such that you're able to create
your own rules for the population, prioritization and dispatching of tasks.

The *scheduler* implements a priority queue for prioritization of tasks to be
performed by the worker(s). In the implementation of the scheduler within KAT
the scheduler is tasked with populating the priority queue with boefje and
normalizer tasks. The scheduler is responsible for maintaining and updating
its internal priority queue.

A priority queue is used, in as such, that it allows us to determine what jobs
should be checked first, or more regularly. Because of the use of a priority
queue we can differentiate between jobs that are to be executed first. E.g.
job's created by the user get precedence over jobs that are created by the
internal rescheduling processes within the scheduler.

Calculations in order to determine the priority of a job is performed by logic
that can/will leverage information from multiple (external) sources, called
`connectors`.

In this document we will outline what the scheduler does in the setup within
KAT and how it is used, and its default configuration. Further on we will
describe how to extend the scheduler to support your specific needs.

### Architecture / Design

In order to get a better overview of how the scheduler is implemented we will
be using the [C4 model](https://c4model.com/) to give an overview of the
scheduler system with their respective level of abstraction.

#### ...


#### C2 Container level:

```mermaid
graph TB
    
    Rocky["Rocky<br/>[webapp]"]
    Octopoes["Octopoes<br/>[graph database]"]
    Katalogus["Katalogus<br/>[software system]"]
    Bytes["Bytes<br/>[software system]"]
    Boefjes["Boefjes<br/>[software system]"]
    Scheduler["Scheduler<br/>[system]"]
    RabbitMQ["RabbitMQ<br/>[message broker]"]

    Rocky--"Create object"-->Octopoes
    Rocky--"Create scan job<br/>HTTP POST"--->Scheduler

    Octopoes--"Get random oois<br/>HTTP GET"-->Scheduler

    RabbitMQ--"Get latest created oois<br/>Get latest raw files<br/>AMQP"-->Scheduler

    Katalogus--"Get available plugins<br/>HTTP GET"-->Scheduler
    Bytes--"Get last run boefje<br/>HTTP GET"-->Scheduler

    Scheduler--"Send task<br/>CELERY send_task"-->Boefjes
```

* The `Scheduler` system combines data from the `Octopoes`, `Katalogus`, `Bytes` and
  `RabbitMQ` systems. With these data it determines what tasks should be
  created and dispatched.

* The `Scheduler` system implements multiple `schedulers` per organisation.

#### C3 Component level:

```mermaid
flowchart TB
    
    %% External services
    Rocky["Rocky<br/>[webapp]"]
    Octopoes["Octopoes<br/>[graph database]"]
    Katalogus["Katalogus<br/>[software system]"]
    Boefjes["Boefjes<br/>[software system]"]
    Normalizers["Normalizers<br/>[software system]"]
    Bytes["Bytes<br/>[software system]"]
    RabbitMQ["RabbitMQ<br/>[message broker]"]

    %% Rocky flow
    Rocky--"Create object"-->Octopoes
    Rocky--"Create scan job<br/>HTTP POST"--->push_queue
    push_queue--"Push job with highest priority"-->BoefjePriorityQueue
    push_queue--"Push job with highest priority"-->NormalizerPriorityQueue
    
    %% External services flow
    Bytes--"Check last run of boefje and ooi<br/>HTTP GET"-->create_tasks_for_ooi
    Katalogus--"Get available boefjes<br/>HTTP GET"--->create_tasks_for_ooi
    Katalogus--"Get availalble normalizers<br/>HTTP GET"-->create_tasks_for_raw_data
    Octopoes--"Get random ooi"--->get_random_object
    RabbitMQ--"Get latest created object<br/>(scan level increase)"-->get_latest_object
    RabbitMQ--"Get latest raw data file<br/>(boefje finished)"-->get_latest_raw_data

    %% Boefje flow
    get_latest_object-->get_random_object-->create_tasks_for_ooi-->rank_boefje-->push_boefje
    push_boefje-->post_push_boefje
    push_boefje--> BoefjePriorityQueue
    post_push_boefje-->Datastore
    post_pop_boefje-->Datastore
    BoefjeDispatcher--"Send task to Boefjes"-->Boefjes    
    
    %% Normalizer flow
    get_latest_raw_data-->create_tasks_for_raw_data-->rank_normalizer-->push_normalizer
    push_normalizer-->post_push_normalizer
    push_normalizer-->NormalizerPriorityQueue
    post_push_normalizer-->Datastore
    post_pop_normalizer-->Datastore
    NormalizerDispatcher--"Send task to Normalizers"-->Normalizers


    subgraph Scheduler["SchedulerApp [module]"]

        subgraph BoefjeScheduler["BoefjeScheduler [class]"]
            subgraph BoefjePopulateQueue["populate_queue() [method]"]
                get_latest_object[["get_latest_object()"]]
                get_random_object[["get_random_object()"]]
                create_tasks_for_ooi[["create_tasks_for_ooi()<br/><br/>* combine ooi with available <br/>boefjes to create tasks<br/>* check if those tasks are able<br/>to run"]]
                rank_boefje[["rank()"]]
                push_boefje[["push()"]]
            end

            post_push_boefje[["post_push()<br/><br/>add tasks to database"]]
            post_pop_boefje[["post_pop()<br/><br/>update tasks in database"]]

            BoefjePriorityQueue(["PriorityQueue"])
            BoefjePriorityQueue-->BoefjeDispatcher
            
            BoefjeDispatcher[["Dispatcher"]]
        end

        subgraph BoefjeDispatcher["BoefjeDispatcher [class]"]
            boefje_dispatch[["dispatch()"]]
        end
        boefje_dispatch-->post_pop_boefje


        subgraph NormalizerScheduler["NormalizerScheduler [class]"]
            subgraph NormalizerPopulateQueue["populate_queue() [method]"]
                get_latest_raw_data[["get_latest_raw_data()"]]
                create_tasks_for_raw_data[["create_tasks_for_raw_data<br/><br/>* based on mime-types<br/>of the raw file, create<br/>normalizer tasks<br/>* check if normalizer is able to run<br/>* update status of boefje task to<br/>completed"]]
                rank_normalizer[["rank()"]]
                push_normalizer[["push()"]]
            end

            post_push_normalizer[["post_push()<br/><br/>add tasks to database"]]
            post_pop_normalizer[["post_pop()<br/><br/>update tasks in database"]]
            
            NormalizerPriorityQueue(["PriorityQueue"])
            NormalizerPriorityQueue-->NormalizerDispatcher

            NormalizerDispatcher[["NormalizerDispatcher"]]
        end

        subgraph NormalizerDispatcher["NormalizerDispatcher [class]"]
            normalizer_dispatch[["dispatch()"]]
        end
        normalizer_dispatch-->post_pop_normalizer

        subgraph Server
            push_queue[["push_queue()<br/>[api endpoint]"]]
        end

        Datastore[("SQLite<br/>[datastore]<br/>(in-memory)")]

    end
```

* The `Scheduler` system implements multiple `schedulers`, one per
  organisation. An individual scheduler contains:

  - A queue
  - A ranker

* A `scheduler` implements the `populate_queue` method. It will:

  - Get the latest created object in a loop, it will try to fill up the queue
    with the latest created objects.

  - When the queue isn't full, it will try and fill up the queue with random
    objects from the octopoes system.

* A `scheduler` implements methods for popping items of the queue and pushing
 off the queue. After the calls to the `pop` and `push` methods a `post_pop()`
 and `post_push` method will be called. This will be used to update the tasks
 in the database.

#### C4 Code level (Condensed class diagram)

```mermaid
classDiagram

    class App {
        +AppContext ctx
        +Dict[str, ThreadRunner] threads
        +Dict[str, Scheduler] schedulers
        +Dict[str, Dispatcher] dispatchers
        +Dict[str, Listener] listeners
        +Server server
        run()
    }

    class Scheduler {
        <<abstract>>
        +AppContext ctx
        +Dict[str, ThreadRunner] threads        
        +PriorityQueue queue
        +Ranker ranker
        populate_queue()
        push_items_to_queue()
        push_item_to_queue()
        pop_item_from_queue()
        post_push()
        post_pop()
        run()
    }

    class PriorityQueue{
        +PriorityQueue[Entry] pq
        pop()
        push()
        peek()
        remove()
    }

    class Entry {
        +int priority
        +PrioritizedItem p_item
        +EntryState state
    }

    class PrioritizedItem {
        +int priority
        +Any item
    }

    class Ranker {
        <<abstract>>
        +AppContext ctx
        rank()
    }

    class Dispatcher {
        +AppContext ctx
        +Scheduler scheduler
        dispatch()
        run()
    }

    class Listener {


    }

    App --|> "many" Scheduler : Implements
    App --|> "many" Dispatcher : Has

    Scheduler --|> "1" PriorityQueue : Has
    Scheduler --|> "1" Ranker : Has

    PriorityQueue --|> "many" Entry : Has

    Entry --|> "1" PrioritizedItem : Has
```

The following describes the main components of the scheduler application:

* `App` - The main application class, which is responsible for starting the
  schedulers. It also contains the server, which is responsible for handling
  the rest api requests. The `App` implements multiple `Scheduler` instances.
  The `run()` method starts the schedulers, the listeners, the monitors,
  the dispatchers, and the server in threads. The `run()` method is the main
  thread of the application.

* `Scheduler` - And implementation of a `Scheduler` class is responsible for
  populating the queue with tasks. Contains has a `PriorityQueue` and a
  `Ranker`. The `run()` method starts the `populate_queue()` method, which
  fill up the queue with tasks. The `run()` method is run in a thread.

* `PriorityQueue` - The queue class, which is responsible for storing the
  tasks.

* `Ranker` - The ranker class, which is responsible for ranking the tasks,
  and can be called from the `Scheduler` class in order to rank the tasks.

* `Dispatcher` - The dispatcher class, which is responsible for dispatching
  the tasks. A `Dispatcher` has a `Scheduler` instance, which it will
  reference on pop off tasks from to be executed. The `run()` method will
  continuously dispatch tasks from the queue. The `run()` method is run in a
  thread.

* `Server` - The server class, which is responsible for handling the HTTP
  requests.
