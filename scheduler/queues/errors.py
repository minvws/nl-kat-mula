class QueueEmptyError(Exception):
    pass


class NotAllowedError(Exception):
    pass


class InvalidPrioritizedItemError(ValueError):
    pass
