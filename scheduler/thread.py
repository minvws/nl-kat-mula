import logging
import threading


class ThreadRunner(threading.Thread):
    """ThreadRunner extends threading.Thread to allow for graceful shutdown
    using event signalling. Additionally to the standard threading.Thread
    attributes we use the following attributes.

    Attributes:
        logger:
            The logger for the class.
        stop_event:
            A threading.Event object used for signalling thread stop events.
        interval:
            A float describing the time between loop iterations.
        exception:
            A python Exception that can be set in order to signify that
            an exception has occured during the execution of the thread.
    """

    logger: logging.Logger
    stop_event: threading.Event
    interval: float
    exception: Exception

    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.stop_event = kwargs.pop("stop_event", None)
        self.interval = kwargs.pop("interval", 0.01)
        self.exception = None

        super().__init__(*args, **kwargs)

    def run(self):
        while not self.stop_event.is_set():
            try:
                self._target(*self._args, **self._kwargs)
            except Exception as e:
                self.exception = e
                self.logger.exception(e)
                self.stop()

            self.stop_event.wait(self.interval)

    def join(self, timeout=None):
        self.logger.debug(f"Stopping thread:")

        self.stop_event.set()
        super().join(timeout)

        self.logger.debug(f"Thread stopped")

    def stop(self):
        self.stop_event.set()
