from __future__ import annotations

import abc
import json
import logging
import queue
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Tuple, Type

import mmh3
import pydantic
from scheduler import models
from scheduler.repositories.sqlalchemy import PriorityQueueStore

from .errors import (InvalidPrioritizedItemError, NotAllowedError,
                     PrioritizedItemNotFoundError, QueueEmptyError,
                     QueueFullError)


class PriorityQueue(abc.ABC):
    """

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
        pq_store: PriorityQueueStore = None,
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
        self.allow_replace: bool = allow_replace
        self.allow_updates: bool = allow_updates
        self.allow_priority_updates: bool = allow_priority_updates
        self.pq_store: PriorityQueueStore = pq_store

    def pop(self) -> Optional[models.PrioritizedItem]:
        """Remove and return the highest priority item from the queue.

        Raises:
            QueueEmptyError: If the queue is empty.
        """
        if self.empty():
            raise QueueEmptyError(f"Queue {self.pq_id} is empty.")

        return self.pq_store.pop(self.pq_id)

    def push(self, p_item: models.PrioritizedItem) -> Optional[models.PrioritizedItem]:
        """Push an item onto the queue.

        Raises:
            NotAllowedError: If the item is not allowed to be pushed.

            InvalidPrioritizedItemError:

            QueueFullError:
        """
        if not isinstance(p_item, models.PrioritizedItem):
            raise InvalidPrioritizedItemError("The item is not a PrioritizedItem")

        if not self._is_valid_item(p_item.data):
            raise InvalidPrioritizedItemError(f"PrioritizedItem must be of type {self.item_type}")

        if self.full():
            raise QueueFullError(f"Queue {self.pq_id} is full.")

        # We try to get the item from the queue by a specified identifier of
        # that item by the implementation of the queue. We don't do this by
        # the item itself or its hash because this might have been changed
        # and we might need to update that.
        item_on_queue = self.get_p_item_by_identifier(p_item)

        item_changed = (
            False
            if not item_on_queue or p_item.data == item_on_queue.data  # FIXM: checking json/dicts here
            else True
        )

        priority_changed = (
            False
            if not item_on_queue or p_item.priority == item_on_queue.priority
            else True
        )

        allowed = False
        if item_on_queue and self.allow_replace:
            allowed = True
        elif self.allow_updates and item_changed and item_on_queue:
            allowed = True
        elif self.allow_priority_updates and priority_changed and item_on_queue:
            allowed = True
        elif not item_on_queue:
            allowed = True

        if not allowed:
            raise NotAllowedError(
                f"[item_on_queue={item_on_queue}, item_changed={item_changed}, priority_changed={priority_changed}, allow_replace={self.allow_replace}, allow_updates={self.allow_updates}, allow_priority_updates={self.allow_priority_updates}]"
            )

        # If already on queue update the item, else create a new one
        item_db = None
        if not item_on_queue:
            identifier = self.create_hash(p_item)
            p_item.hash = identifier
            item_db = self.pq_store.push(self.pq_id, p_item)
        else:
            self.pq_store.update(self.pq_id, p_item)
            item_db = self.get_p_item_by_identifier(p_item)

        if not item_db:
            raise PrioritizedItemNotFoundError(f"Item {p_item} not found on queue {self.pq_id}")

        return item_db

    def peek(self, index: int) -> Optional[models.PrioritizedItem]:
        task = self.pq_store.peek(self.pq_id, index)
        if task is None:
            return None

        return models.PrioritizedItem(item=task.item, priority=task.priority)

    def remove(self, p_item: models.PrioritizedItem) -> None:
        self.pq_store.remove(self.pq_id, p_item)

    def empty(self) -> bool:
        return self.pq_store.empty(self.pq_id)

    def qsize(self) -> int:
        return self.pq_store.qsize(self.pq_id)

    def full(self) -> bool:
        current_size = self.qsize()
        if self.maxsize is None or self.maxsize == 0:
            return False

        return current_size >= self.maxsize

    def is_item_on_queue(self, p_item: models.PrioritizedItem) -> bool:
        identifier = self.create_hash(p_item)
        item = self.pq_store.get_item_by_hash(self.pq_id, identifier)
        if item is None:
            return False

        return True

    def get_p_item_by_identifier(self, p_item: models.PrioritizedItem) -> bool:
        identifier = self.create_hash(p_item)
        item = self.pq_store.get_item_by_hash(self.pq_id, identifier)
        return item

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

    def dict(self) -> Dict[str, Any]:
        """Return a dict representation of the queue."""
        return {
            "id": self.pq_id,
            "size": self.qsize(),
            "maxsize": self.maxsize,
            "item_type": self.item_type.__name__,
            "allow_replace": self.allow_replace,
            "allow_updates": self.allow_updates,
            "allow_priority_updates": self.allow_priority_updates,
            "pq": self.pq_store.get_items_by_scheduler_id(self.pq_id),
        }


    @abc.abstractmethod
    def create_hash(self, p_item: models.PrioritizedItem) -> str:
        raise NotImplementedError
