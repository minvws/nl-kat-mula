from scheduler import context

from . import Scheduler

if __name__ == "__main__":
    app = Scheduler(ctx=context.AppContext())
    app.run()
