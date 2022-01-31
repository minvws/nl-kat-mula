import logging

from scheduler import context

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    ctx = context.AppContext()

    logger.info("Starting scheduler...")
