import heapq
import json
import logging
import queue
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Set, Tuple, Union

import pydantic


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

    def __attrs(self) -> Tuple[int, Any]:
        return (self.priority, self.item)

    def __hash__(self) -> int:
        return hash(self.__attrs())

    def __eq__(self, other) -> bool:
        return isinstance(other, PrioritizedItem) and self.__attrs() == other.__attrs()


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
        return {"priority": self.priority, "item": self.p_item.dict(), "state": self.state.value}

    def __attrs(self) -> Tuple[int, Any]:
        return (self.priority, self.p_item, self.state)

    def __hash__(self) -> int:
        return hash(self.__attrs())

    def __lt__(self, other) -> bool:
        return self.priority < other.priority

    def __eq__(self, other) -> bool:
        return isinstance(other, Entry) and self.__attrs() == other.__attrs()


class PriorityQueue:
    """Thread-safe implementation of a priority queue.

    When a multi-processing implementation is required, see:
    https://docs.python.org/3/library/multiprocessing.html#multiprocessing.Queue

    Reference:
        https://docs.python.org/3/library/queue.html#queue.PriorityQueue

    Attributes:
        logger:
            The logger for the class.
        id:
            A sting representing the identifier of the priority queue.
        maxsize:
            A integer representing the maximum size of the queue.
        item_type:
            A pydantic.BaseModel that describes the type of the items on the
            queue.
        pq:
            A queue.PriorityQueue object.
        timeout:
            An integer defining the timeout for blocking operations.
        entry_finder:
            A dict that maps items (python objects) to their corresponding
            entries in the queue.
        allow_duplicates:
            A boolean that defines if the queue allows duplicates. When set to
            True, the queue will not remove items from the queue when
            duplicate items are added.
        allow_updates:
            A boolean that defines if the queue allows updates. When set to
            True, the queue will not remove items from the queue when the
            attributes of an item are updated.
        allow_priority_updates:
            A boolean that defines if the queue allows updates. When set to
            True, the queue will not remove items from the queue when the
            priority of an item is updated.
    """

    def __init__(self, id: str, maxsize: int, item_type: pydantic.BaseModel,
                 allow_duplicates: bool = False, allow_updates: bool = False,
                 allow_priority_updates: bool = False):
        """Initialize the priority queue.

        Args:
            id: The id of the queue.
            maxsize: The maximum size of the queue.
            item_type (pydantic.BaseModel): The type of the items in the queue.
        allow_duplicates:
            A boolean that defines if the queue allows duplicates. When set to
            True, the queue will not remove items from the queue when
            duplicate items are added.
        allow_updates:
            A boolean that defines if the queue allows updates. When set to
            True, the queue will not remove items from the queue when the
            attributes of an item are updated.
        allow_priority_updates:
            A boolean that defines if the queue allows updates. When set to
            True, the queue will not remove items from the queue when the
            priority of an item is updated.
        """
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.id: str = id
        self.maxsize: int = maxsize
        self.item_type: pydantic.BaseModel = item_type
        self.pq: queue.PriorityQueue = queue.PriorityQueue(maxsize=self.maxsize)
        self.timeout: int = 5
        self.entry_finder: Dict[Any, Entry] = {}
        self.allow_duplicates: bool = allow_duplicates
        self.allow_updates: bool = allow_updates
        self.allow_priority_updates: bool =  allow_priority_updates

    def pop(self) -> Union[PrioritizedItem, None]:
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
                item: Union[PrioritizedItem, None]
                state: EntryState

                entry = self.pq.get(block=True, timeout=self.timeout)

                # When we reach an item that isn't removed, we can return it
                if entry.state is not EntryState.REMOVED:
                    del self.entry_finder[entry.p_item.item]
                    return entry.p_item
            except queue.Empty:
                self.logger.warning(f"Queue {self.id} is empty")
                return None

    def push(self, p_item: PrioritizedItem) -> None:
        """Push an item with priority into the queue. When timeout is set it
        will block if necessary until a free slot is available. It raises the
        Full exception if no free slot was available within that time.

        Args:
            p_item: The item to be pushed into the queue.

        Raises:
            ValueError: If the item is not valid.

        Reference:
            https://docs.python.org/3/library/queue.html#queue.PriorityQueue.put
        """
        if not self._is_valid_item(p_item.item):
            raise ValueError(f"PrioritizedItem must be of type {self.item_type.__name__}")

        on_queue = self.is_item_on_queue(p_item.item)
        item_changed = False if not on_queue or p_item == self.entry_finder[p_item.item].p_item else True
        priority_changed = False if not on_queue or p_item.priority == self.entry_finder[p_item.item].p_item.priority else True

        if not self.allow_duplicates and on_queue:
            self.logger.warning(f"Item {p_item.item} already in queue {self.id} [queue={self.id} p_item={p_item}]")
            return
        elif not self.allow_updates and not item_changed and on_queue:
            self.logger.warning(f"Item {p_item.item} not in queue, or did not change in queue {self.id} [queue={self.id} p_item={p_item}]")
            return
        elif not self.allow_priority_updates and not priority_changed and on_queue:
            self.logger.warning(
                f"Item {p_item.item} not in queue, or priority did not change in queue {self.id} [queue={self.id} p_item={p_item}]"
            )
            return

        # Set item as removed in entry_finder when it is already present,
        # since we're updating the entry. Using an Entry here acts as a
        # pointer to the entry in the queue and the entry_finder.
        if p_item.item in self.entry_finder:
            entry = self.entry_finder.pop(p_item.item)
            entry.state = EntryState.REMOVED

        entry = Entry(p_item=p_item, state=EntryState.ADDED)
        self.entry_finder[p_item.item] = entry

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
        item = self.pq.queue[index]
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
        if not self._is_valid_item(p_item.item):
            raise ValueError(f"Item must be of type {self.item_type.__name__}")

        if p_item.item in self.entry_finder:
            entry = self.entry_finder.pop(p_item.item)
            entry.state = EntryState.REMOVED

    def is_item_on_queue(self, item: Any) -> bool:
        """Check if an item is on the queue.

        Args:
            item: The item to be checked.

        Raises:
            ValueError: If the item is not valid.
        """
        if not self._is_valid_item(item):
            raise ValueError(f"Item must be of type {self.item_type.__name__}")

        return item in self.entry_finder

    def _is_valid_item(self, item: Any) -> bool:
        """Validate the item to be pushed into the queue.

        Args:
            item: The item to be validated.

        Returns:
            A boolean, True if the item is valid, False otherwise.
        """
        try:
            pydantic.parse_obj_as(self.item_type, item)
        except pydantic.ValidationError:
            return False

        return True

    def dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "size": self.pq.qsize(),
            "maxsize": self.maxsize,
            "pq": [self.pq.queue[i].dict() for i in range(self.pq.qsize())],  # TODO: maybe overkill
        }

    def json(self) -> str:
        return json.dumps(self.dict())

    def empty(self) -> bool:
        return self.pq.empty()

    def __len__(self) -> int:
        return self.pq.qsize()
