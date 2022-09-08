from __future__ import annotations

import json
import logging
import queue
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Tuple, Type

import pydantic
from scheduler import models
from scheduler.repositories.sqlalchemy import PriorityQueueStore

from .errors import (InvalidPrioritizedItemError, NotAllowedError,
                     QueueEmptyError, QueueFullError)


class EntryState(str, Enum):
    """A Enum describing the state of an entry on the priority queue."""

    ADDED = "added"
    REMOVED = "removed"


@dataclass(order=True)
class PrioritizedItem:
    """Solves the issue non-comparable tasks to ignore the task item and only
    compare the priority.

    Attributes:
        priority:
            An integer describing the priority of the item.
        item:
            A python object that is attached to the prioritized item.
    """

    def __init__(self, priority: int, item: Any):
        self.priority: int = priority
        self.item: Any = item

    def dict(self) -> Dict[str, Any]:
        return {"priority": self.priority, "item": self.item}

    def json(self) -> str:
        return json.dumps(self.dict())

    def attrs(self) -> Tuple[int, Any]:
        return (self.priority, self.item)

    # FIXME: hash
    def __hash__(self) -> int:
        return hash(self.attrs())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PrioritizedItem):
            return False
        return self.attrs() == other.attrs()


class Entry:
    """A class that represents an entry on the priority queue.

    Attributes:
        priority:
            An integer describing the priority of the item.
        p_item:
            A PrioritizedItem object.
        state:
            An EntryState object.
    """

    def __init__(self, p_item: PrioritizedItem, state: EntryState):
        self.priority: int = p_item.priority
        self.p_item: PrioritizedItem = p_item
        self.state: EntryState = state

    def dict(self) -> Dict[str, Any]:
        return {"priority": self.priority, "p_item": self.p_item.dict(), "state": self.state.value}

    def attrs(self) -> Tuple[int, PrioritizedItem, EntryState]:
        return (self.priority, self.p_item, self.state)

    # FIXME: hash
    def __hash__(self) -> int:
        return hash(self.attrs())

    def __lt__(self, other: Any) -> bool:
        if self.priority < other.priority:
            return True

        return False

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entry):
            return False
        return self.attrs() == other.attrs()


class Base:
    """Base class for priority queues

    Attributes:
        logger:
            The logger for the class.
        pq_id:
            A sting representing the identifier of the priority queue.
        maxsize:
            A integer representing the maximum size of the queue.
        item_type:
            A pydantic.BaseModel that describes the type of the items on the
            queue.
        timeout:
            An integer defining the timeout for blocking operations.
        allow_replace:
            A boolean that defines if the queue allows replacing an item. When
            set to True, it will update the item on the queue. It will set the
            state of the item to REMOVED in the queue, and the updated entry
            will be added to the queue, and the item will be removed the
            entry_finder.
        allow_updates:
            A boolean that defines if the queue allows updates of items on the
            queue. When set to True, it will update the item on the queue. It
            will set the state of the item to REMOVED in the queue, and the
            updated entry will be added to the queue, and the item will be
            removed the entry_finder.
        allow_priority_updates:
            A boolean that defines if the queue allows priority updates of
            items on the queue. When set to True, it will update the item on
            the queue. It will set the state of the item to REMOVED in the
            queue, and the updated entry will be added to the queue, and the
            item will be removed the entry_finder.
    """

    def __init__(
        self,
        pq_id: str,
        maxsize: int,
        item_type: Type[pydantic.BaseModel],
        allow_replace: bool = False,
        allow_updates: bool = False,
        allow_priority_updates: bool = False,
    ):
        """Initialize the priority queue.

        Args:
            pq_id:
                The id of the queue.
            maxsize:
                The maximum size of the queue.
            item_type:
                The type of the items in the queue.
        """
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.pq_id: str = pq_id
        self.maxsize: int = maxsize
        self.item_type: Type[pydantic.BaseModel] = item_type
        self.timeout: int = 5
        self.allow_replace: bool = allow_replace
        self.allow_updates: bool = allow_updates
        self.allow_priority_updates: bool = allow_priority_updates

    # TODO: abc and methods


class PriorityQueue(Base):
    """Thread-safe in-memory implementation of a priority queue.

    When a multi-processing implementation is required, see:
    https://docs.python.org/3/library/multiprocessing.html#multiprocessing.Queue

    Reference:
        https://docs.python.org/3/library/queue.html#queue.PriorityQueue

    Attributes:
        pq:
            A queue.PriorityQueue object.
        entry_finder:
            A dict that maps items (python objects) to their corresponding
            entries in the queue.
    """

    def __init__(
        self,
        pq_id: str,
        maxsize: int,
        item_type: Type[pydantic.BaseModel],
        allow_replace: bool = False,
        allow_updates: bool = False,
        allow_priority_updates: bool = False,
    ):
        super().__init__(
            pq_id=pq_id,
            maxsize=maxsize,
            item_type=item_type,
            allow_replace=allow_replace,
            allow_updates=allow_updates,
            allow_priority_updates=allow_priority_updates,
        )

        self.entry_finder: Dict[Any, Entry] = {}
        self.pq: queue.PriorityQueue = queue.PriorityQueue(maxsize=self.maxsize)

    def pop(self) -> PrioritizedItem:
        """Pop the item with the highest priority from the queue. If optional
        args block is true and timeout is None (the default), block if
        necessary until an item is available. If timeout is a positive number,
        it blocks at most timeout seconds and raises the Empty exception if no
        item was available within that time. Otherwise (block is false), return
        an item if one is immediately available, else raise the Empty exception
        (timeout is ignored in that case).

        Reference:
            https://docs.python.org/3/library/queue.html#queue.PriorityQueue.get
        """
        while True:
            try:
                entry = self.pq.get(block=True, timeout=self.timeout)

                # When we reach an item that isn't removed, we can return it
                if entry.state is not EntryState.REMOVED:
                    del self.entry_finder[self.get_item_identifier(entry.p_item.item)]
                    return entry.p_item
            except queue.Empty as exc:
                raise QueueEmptyError(f"Queue {self.pq_id} is empty.") from exc

    def push(self, p_item: PrioritizedItem) -> None:
        """Push an item with priority into the queue. When timeout is set it
        will block if necessary until a free slot is available. It raises the
        Full exception if no free slot was available within that time.

        Args:
            p_item: The item to be pushed into the queue.

        Raises:
            ValueError: If the item is not valid.
            InvalidPrioritizedItemError: If the item is not valid.
            Full: If the queue is full.

        Reference:
            https://docs.python.org/3/library/queue.html#queue.PriorityQueue.put
        """
        if not isinstance(p_item, PrioritizedItem):
            raise InvalidPrioritizedItemError("The item is not a PrioritizedItem")

        if not self._is_valid_item(p_item.item):
            raise InvalidPrioritizedItemError(f"PrioritizedItem must be of type {self.item_type}")

        if self.maxsize is not None and self.maxsize != 0 and self.qsize() == self.maxsize:
            raise QueueFullError(f"Queue {self.pq_id} is full.")

        on_queue = self.is_item_on_queue(p_item.item)

        item_changed = (
            False
            if not on_queue or p_item.item == self.entry_finder[self.get_item_identifier(p_item.item)].p_item.item
            else True
        )

        priority_changed = (
            False
            if not on_queue or p_item.priority == self.entry_finder[self.get_item_identifier(p_item.item)].priority
            else True
        )

        allowed = False
        if on_queue and self.allow_replace:
            allowed = True
        elif self.allow_updates and item_changed and on_queue:
            allowed = True
        elif self.allow_priority_updates and priority_changed and on_queue:
            allowed = True
        elif not on_queue:
            allowed = True

        if not allowed:
            raise NotAllowedError(
                f"[on_queue={on_queue}, item_changed={item_changed}, priority_changed={priority_changed}, allow_replace={self.allow_replace}, allow_updates={self.allow_updates}, allow_priority_updates={self.allow_priority_updates}]"
            )

        # Set item as removed in entry_finder when it is already present,
        # since we're updating the entry. Using an Entry here acts as a
        # pointer to the entry in the queue and the entry_finder.
        if self.get_item_identifier(p_item.item) in self.entry_finder:
            entry = self.entry_finder.pop(self.get_item_identifier(p_item.item))
            entry.state = EntryState.REMOVED

        entry = Entry(p_item=p_item, state=EntryState.ADDED)
        self.entry_finder[self.get_item_identifier(p_item.item)] = entry

        self.pq.put(
            item=entry,
            block=True,
            timeout=self.timeout,
        )

    def peek(self, index: int) -> Entry:
        """Return the priority queue Entry without removing it from the queue.

        Reference:
            https://docs.python.org/3/library/queue.html#queue.PriorityQueue.peek

        Args:
            index:
                An integer describing the index of item on the queue that you
                want to inspect.
        """
        item: Entry = self.pq.queue[index]
        return item

    def remove(self, p_item: PrioritizedItem) -> None:
        """Remove an item from the queue.

        Args:
            item: The item to be removed.

        Raises:
            ValueError: If the item is not valid.

        Reference:
            https://docs.python.org/3/library/queue.html#queue.PriorityQueue.remove
        """

        if self.get_item_identifier(p_item.item) in self.entry_finder:
            entry = self.entry_finder.pop(self.get_item_identifier(p_item.item))
            entry.state = EntryState.REMOVED

    def is_item_on_queue(self, item: Any) -> bool:
        """Check if an item is on the queue.

        Args:
            item: The item to be checked.

        Raises:
            ValueError: If the item is not valid.
        """
        identifier = self.get_item_identifier(item)
        return identifier in self.entry_finder

    def get_item_identifier(self, item: Any) -> Any:
        """Get the identifier of an item. This is needed to construct an
        identifier for the item in the entry_finder. The naive implementation
        is using the item object as the key value for the entry_finder. For
        custom implementations you would likely want to override this method.

        Args:
            item: The item to be checked.

        Returns:
            The identifier of the item.
        """
        return item

    def full(self) -> bool:
        """Return True if the queue is full."""
        if self.maxsize is None or self.maxsize == 0:
            return False

        return self.pq.full()

    def _is_valid_item(self, item: Any) -> bool:
        """Validate the item to be pushed into the queue.

        Args:
            item: The item to be validated.

        Returns:
            A boolean, True if the item is valid, False otherwise.
        """
        try:
            self.item_type.parse_obj(item)
        except pydantic.ValidationError:
            return False

        return True

    def qsize(self) -> int:
        """Return the size of the queue."""
        return self.pq.qsize()

    def dict(self) -> Dict[str, Any]:
        return {
            "id": self.pq_id,
            "size": self.pq.qsize(),
            "maxsize": self.maxsize,
            "allow_replace": self.allow_replace,
            "allow_updates": self.allow_updates,
            "allow_priority_updates": self.allow_priority_updates,
            "pq": [self.pq.queue[i].dict() for i in range(self.pq.qsize())],
        }

    def json(self) -> str:
        return json.dumps(self.dict())

    def empty(self) -> bool:
        return self.pq.empty()

    def __len__(self) -> int:
        return self.pq.qsize()


class DataStorePriorityQueue(Base):

    def __init__(
        self,
        pq_id: str,
        maxsize: int,
        item_type: Type[pydantic.BaseModel],
        allow_replace: bool = False,
        allow_updates: bool = False,
        allow_priority_updates: bool = False,
        pq_store: PriorityQueueStore = None,
    ):
        super().__init__(
            pq_id=pq_id,
            maxsize=maxsize,
            item_type=item_type,
            allow_replace=allow_replace,
            allow_updates=allow_updates,
            allow_priority_updates=allow_priority_updates,
        )

        self.pq_store: PriorityQueueStore = pq_store

    def pop(self) -> PrioritizedItem:
        """Remove and return the highest priority item from the queue.

        Raises:
            QueueEmptyError: If the queue is empty.
        """
        if self.empty():
            raise QueueEmptyError(f"Queue {self.pq_id} is empty.")

        task = self.pq_store.pop(self.pq_id)
        if task is None:
            return None

        return PrioritizedItem(item=task.item, priority=task.priority)

    def push(self, p_item: PrioritizedItem) -> None:
        """Push an item onto the queue.

        Raises:
            NotAllowedError: If the item is not allowed to be pushed.
        """
        if not isinstance(p_item, PrioritizedItem):
            raise InvalidPrioritizedItemError("The item is not a PrioritizedItem")

        if not self._is_valid_item(p_item.item):
            raise InvalidPrioritizedItemError(f"PrioritizedItem must be of type {self.item_type}")

        if self.maxsize is not None and self.maxsize != 0 and self.qsize() == self.maxsize:
            raise QueueFullError(f"Queue {self.pq_id} is full.")

        task_on_queue = self.get_task_by_item(p_item.item)

        item_changed = (
            False
            if not task_on_queue or p_item.item == task_on_queue.item
            else True
        )

        priority_changed = (
            False
            if not task_on_queue or task_on_queue.priority == p_item.priority
            else True
        )

        allowed = False
        if on_queue and self.allow_replace:
            allowed = True
        elif self.allow_updates and item_changed and on_queue:
            allowed = True
        elif self.allow_priority_updates and priority_changed and on_queue:
            allowed = True
        elif not on_queue:
            allowed = True

        if not allowed:
            raise NotAllowedError(
                f"[on_queue={on_queue}, item_changed={item_changed}, priority_changed={priority_changed}, allow_replace={self.allow_replace}, allow_updates={self.allow_updates}, allow_priority_updates={self.allow_priority_updates}]"
            )

        # If already on queue update the item, else create a new one
        task = models.Task(
            id=p_item.item.id,
            hash=p_item.item.hash,
            scheduler_id=self.pq_id,
            task=models.QueuePrioritizedItem(**p_item.dict()),
            status=models.TaskStatus.QUEUED,
            created_at=datetime.datetime.now(),
            modified_at=datetime.datetime.now(),
        )

        if task_on_queue:
            task_db = self.pq_store.update_task(self.pq_id, task)
        else:
            task_db = self.pq_store.push(self.pq_id, task)

        if task_db is None:
            raise IndexError  # TODO: Better error

        return task_db

    # TODO: change this from the super class as well Entry to PrioritizedItem
    def peek(self, index: int) -> PrioritizedItem:
        task = self.pq_store.peek(self.pq_id, index)
        if task is None:
            return None

        return PrioritizedItem(item=task.item, priority=task.priority)

    def remove(self, p_item: PrioritizedItem) -> None:
        self.pq_store.remove(self.pq_id, p_item)

    def is_item_on_queue(self, item: Any) -> bool:
        identifier = self.get_item_identifier(item)

        task = self.pq_store.get_task_by_hash(self.pq_id, identifier)
        if task is None:
            return False

        return True

    def get_task_by_item(self, item: Any) -> bool:
        identifier = self.get_item_identifier(item)
        task = self.pq_store.get_task_by_hash(self.pq_id, identifier)
        return task

    def full(self) -> bool:
        current_size = self.qsize()
        if self.maxsize is None or self.maxsize == 0:
            return False

        return current_size >= self.maxsize

    def empty(self) -> bool:
        return self.pq_store.empty(self.pq_id)

    def qsize(self) -> int:
        return self.pq_store.qsize(self.pq_id)

    # TODO
    def dict(self) -> Dict[str, Any]:
        raise NotImplementedError

    def json(self) -> str:
        return json.dumps(self.dict())

    def _is_valid_item(self, item: Any) -> bool:
        """Validate the item to be pushed into the queue.

        Args:
            item: The item to be validated.

        Returns:
            A boolean, True if the item is valid, False otherwise.
        """
        try:
            self.item_type.parse_obj(item)
        except pydantic.ValidationError:
            return False

        return True
