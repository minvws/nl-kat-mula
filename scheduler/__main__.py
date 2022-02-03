import logging

from scheduler import server

from . import Scheduler

if __name__ == "__main__":
    app = Scheduler()
    app.run()
