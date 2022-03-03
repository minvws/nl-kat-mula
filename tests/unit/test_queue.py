import copy
import unittest
import uuid

import pydantic
from scheduler import queue


def create_p_item(priority: int):
    return queue.PrioritizedItem(
        priority=priority,
        item=TestModel(),
    )


class TestModel(pydantic.BaseModel):
    id: str = uuid.uuid4().hex
    name: str = uuid.uuid4().hex

    def __hash__(self):
        return hash((self.id, self.name))


class PriorityQueueTestCase(unittest.TestCase):
    def setUp(self):
        self.pq = queue.PriorityQueue(
            id="test-queue",
            maxsize=10,
            item_type=TestModel,
        )
        self.pq.entry_finder = {}

        self._check_queue_empty()

    def tearDown(self):
        del self.pq.entry_finder
        del self.pq

    def _check_queue_empty(self):
        self.assertEqual(len(self.pq), 0)
        self.assertEqual(len(self.pq.entry_finder), 0)

    def test_push(self):
        """When adding an item to the priority queue, the item should be
        added"""
        item = create_p_item(priority=1)
        self.pq.push(p_item=item)

        self.assertEqual(len(self.pq), 1)
        self.assertEqual(len(self.pq.entry_finder), 1)

    def test_update_changed_item(self):
        """When updating an item that is already in the queue, the item should
        NOT be updated and the queue should not be affected.
        """
        # Add an item to the queue
        initial_item = create_p_item(priority=2)
        self.pq.push(p_item=initial_item)

        # Update item
        updated_item = copy.deepcopy(initial_item)
        updated_item.item.name = "updated"
        self.pq.push(p_item=updated_item)

        # PriorityQueue should have 1 item
        self.assertEqual(len(self.pq), 1)
        self.assertEqual(len(self.pq.entry_finder), 1)

    def test_update_priority_higher(self):
        """When updating the priority of the initial item on the priority queue
        to a higher priority, the updated item should be added to the queue,
        the initial item should be marked as removed, and the initial removed
        from the entry_finder.
        """
        # Add an item to the queue
        initial_item = create_p_item(priority=2)
        self.pq.push(p_item=initial_item)

        # Update priority of the item
        updated_item = copy.deepcopy(initial_item)
        updated_item.priority = 1
        self.pq.push(p_item=updated_item)

        # PriorityQueue should have 2 items (one initial with entry state
        # removed, one updated)
        self.assertEqual(len(self.pq), 2)
        self.assertEqual(len(self.pq.entry_finder), 1)

        first_item_priority, first_item, first_item_state = self.pq.peek(0)
        last_item_priority, last_item, last_item_state = self.pq.peek(-1)

        # Last item should be an item with, EntryState.REMOVED
        self.assertEqual(last_item_priority, 2)
        self.assertEqual(last_item, initial_item)
        self.assertEqual(last_item_state, queue.EntryState.REMOVED)

        # First item should be the updated item
        self.assertEqual(first_item_priority, 1)
        self.assertEqual(first_item, updated_item)
        self.assertEqual(first_item_state, queue.EntryState.ADDED)

        # When popping off the queue you should end up with the updated_item
        # that now has the highest priority.
        popped_item = self.pq.pop()
        self.assertEqual(popped_item, updated_item)

        # The queue should now have 1 item and that was the item marked
        # as removed.
        self.assertEqual(len(self.pq), 1)
        self.assertEqual(len(self.pq.entry_finder), 0)

    def test_update_priority_lower(self):
        """When updating the priority of the initial item on the priority queue
        to a lower priority, the updated item should be added to the queue,
        the initial item should be marked as removed, and the initial removed
        from the entry_finder.
        """
        # Add an item to the queue
        initial_item = create_p_item(priority=1)
        self.pq.push(p_item=initial_item)

        # Update priority of the item
        updated_item = copy.deepcopy(initial_item)
        updated_item.priority = 2
        self.pq.push(p_item=updated_item)

        # PriorityQueue should have 2 items (one initial with entry state
        # removed, one updated)
        self.assertEqual(len(self.pq), 2)
        self.assertEqual(len(self.pq.entry_finder), 1)

        first_item_priority, first_item, first_item_state = self.pq.peek(0)
        last_item_priority, last_item, last_item_state = self.pq.peek(-1)

        # Last item should be then updated item
        self.assertEqual(last_item_priority, 2)
        self.assertEqual(last_item, updated_item)
        self.assertEqual(last_item_state, queue.EntryState.ADDED)

        # First item should be the initial item, with EntryState.REMOVED
        self.assertEqual(first_item_priority, 1)
        self.assertEqual(first_item, initial_item)
        self.assertEqual(first_item_state, queue.EntryState.REMOVED)

        # When popping off the queue you should end up with the updated_item
        # that now has the lowest priority.
        popped_item = self.pq.pop()
        self.assertEqual(popped_item, updated_item)

        # The queue should now have 1 item, because the removed item was
        # discarded while popping
        self.assertEqual(len(self.pq), 0)
        self.assertEqual(len(self.pq.entry_finder), 0)

    def test_push_duplicate(self):
        """When pushing an item that is already in the queue, and the priority
        of the item hasn't changed the item shouldn't be pushed.
        """
        # Add an item to the queue
        first_item = create_p_item(priority=1)
        self.pq.push(p_item=first_item)

        self.assertEqual(len(self.pq), 1)
        self.assertEqual(len(self.pq.entry_finder), 1)

        # Add the same item again
        self.pq.push(p_item=first_item)

        self.assertEqual(len(self.pq), 1)
        self.assertEqual(len(self.pq.entry_finder), 1)

    def test_remove_item(self):
        """When removing an item from the queue, the item should be marked as
        removed, and the item should be removed from the entry_finder.
        """
        # Add an item to the queue
        item = create_p_item(priority=1)
        self.pq.push(p_item=item)

        self.assertEqual(len(self.pq), 1)
        self.assertEqual(len(self.pq.entry_finder), 1)

        # Remove the item
        self.pq.remove(item)

        first_item_priority, first_item, first_item_state = self.pq.peek(0)

        # First item should be the item with EntryState.REMOVED
        self.assertEqual(first_item_priority, 1)
        self.assertEqual(first_item, item)
        self.assertEqual(first_item_state, queue.EntryState.REMOVED)

        # The queue should now have 1 item and that was the item marked
        # as removed.
        self.assertEqual(len(self.pq), 1)
        self.assertEqual(len(self.pq.entry_finder), 0)

    def test_pop(self):
        pass

    def test_pop_queue_empty(self):
        pass

    def test_test(self):
        pass
