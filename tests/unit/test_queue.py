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


class TestPriorityQueue(queue.PriorityQueue):
    def get_item_identifier(self, item: TestModel):
        return item.id


class PriorityQueueTestCase(unittest.TestCase):
    def setUp(self):
        self.pq = TestPriorityQueue(
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

    def test_push_replace_not_allowed(self):
        """When pushing an item that is already in the queue the item
        shouldn't be pushed.
        """
        # Set queue to not allow duplicates
        self.pq.allow_replace = False

        # Add an item to the queue
        first_item = create_p_item(priority=1)
        self.pq.push(p_item=first_item)

        self.assertEqual(len(self.pq), 1)
        self.assertEqual(len(self.pq.entry_finder), 1)

        # Add the same item again
        self.pq.push(p_item=first_item)

        self.assertEqual(len(self.pq), 1)
        self.assertEqual(len(self.pq.entry_finder), 1)

    def test_push_replace_allowed(self):
        """When pushing an item that is already in the queue, but the queue
        allows duplicates, the item should be pushed.
        """
        # Set queue to allow duplicates
        self.pq.allow_replace = True

        # Add an item to the queue
        first_item = create_p_item(priority=1)
        self.pq.push(p_item=first_item)

        self.assertEqual(len(self.pq), 1)
        self.assertEqual(len(self.pq.entry_finder), 1)

        # Add the same item again
        self.pq.push(p_item=first_item)

        self.assertEqual(len(self.pq), 2)
        self.assertEqual(len(self.pq.entry_finder), 1)

        # TODO: check if the item on the queue is the replaced item

    def test_push_updates_not_allowed(self):
        """When pushing an item that is already in the queue, and the item is
        updated, the item shouldn't be pushed.
        """
        # Set queue to not allow updates
        self.pq.allow_updates = False

        # Add an item to the queue
        first_item = create_p_item(priority=1)
        self.pq.push(p_item=first_item)

        self.assertEqual(len(self.pq), 1)
        self.assertEqual(len(self.pq.entry_finder), 1)

        # Update the item
        first_item.item.name = "updated-name"

        # Add the same item again
        self.pq.push(p_item=first_item)

        self.assertEqual(len(self.pq), 1)
        self.assertEqual(len(self.pq.entry_finder), 1)

    def test_push_updates_allowed(self):
        """When pushing an item that is already in the queue, and the item is
        updated, but the queue allows item updates, the item should be pushed.
        """
        # Set queue to allow updates
        self.pq.allow_updates = True

        # Add an item to the queue
        initial_item = create_p_item(priority=1)
        self.pq.push(p_item=initial_item)

        self.assertEqual(len(self.pq), 1)
        self.assertEqual(len(self.pq.entry_finder), 1)

        # Update the item
        updated_item = copy.deepcopy(initial_item)
        updated_item.item.name = "updated-name"

        # Add the same item again
        self.pq.push(p_item=updated_item)

        # PriorityQueue should have 2 items (one initial with entry state
        # removed, one updated)
        self.assertEqual(len(self.pq), 2)
        self.assertEqual(len(self.pq.entry_finder), 1)

        # TODO: check if the item on the queue is the updated item

    def test_push_priority_updates_not_allowed(self):
        """When pushing an item that is already in the queue, and the item
        priority is updated, the item shouldn't be pushed.
        """
        # Set queue to allow updates
        self.pq.allow_priority_updates = False

        # Add an item to the queue
        initial_item = create_p_item(priority=1)
        self.pq.push(p_item=initial_item)

        self.assertEqual(len(self.pq), 1)
        self.assertEqual(len(self.pq.entry_finder), 1)

        # Update the item
        updated_item = copy.deepcopy(initial_item)
        updated_item.priority = 100

        # Add the same item again
        self.pq.push(p_item=updated_item)

        self.assertEqual(len(self.pq), 1)
        self.assertEqual(len(self.pq.entry_finder), 1)

    def test_push_priority_updates_allowed(self):
        """When pushing an item that is already in the queue, and the item
        priority is updated, the item should be pushed.
        """
        # Set queue to allow updates
        self.pq.allow_priority_updates = True

        # Add an item to the queue
        initial_item = create_p_item(priority=1)
        self.pq.push(p_item=initial_item)

        self.assertEqual(len(self.pq), 1)
        self.assertEqual(len(self.pq.entry_finder), 1)

        # Update the item
        updated_item = copy.deepcopy(initial_item)
        updated_item.priority = 100

        # Add the same item again
        self.pq.push(p_item=updated_item)

        # PriorityQueue should have 2 items (one initial with entry state
        # removed, one updated)
        self.assertEqual(len(self.pq), 2)
        self.assertEqual(len(self.pq.entry_finder), 1)

        # TODO: check if the item on the queue is the updated item

    def test_update_priority_higher(self):
        """When updating the priority of the initial item on the priority queue
        to a higher priority, the updated item should be added to the queue,
        the initial item should be marked as removed, and the initial removed
        from the entry_finder.
        """
        # Set queue to allow updates
        self.pq.allow_priority_updates = True

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

        first_entry = self.pq.peek(0)
        last_entry = self.pq.peek(-1)

        # Last item should be an item with, EntryState.REMOVED
        self.assertEqual(last_entry.priority, 2)
        self.assertEqual(last_entry.p_item, initial_item)
        self.assertEqual(last_entry.state, queue.EntryState.REMOVED)

        # First item should be the updated item
        self.assertEqual(first_entry.priority, 1)
        self.assertEqual(first_entry.p_item, updated_item)
        self.assertEqual(first_entry.state, queue.EntryState.ADDED)

        # Item in entry_finder should be the updated item
        item = self.pq.entry_finder[self.pq.get_item_identifier(updated_item.item)]
        self.assertEqual(item.priority, updated_item.priority)
        self.assertEqual(item.p_item, updated_item)
        self.assertEqual(item.state, queue.EntryState.ADDED)

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
        # Set queue to allow updates
        self.pq.allow_priority_updates = True

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

        first_entry = self.pq.peek(0)
        last_entry = self.pq.peek(-1)

        # Last item should be the updated item
        self.assertEqual(last_entry.priority, 2)
        self.assertEqual(last_entry.p_item, updated_item)
        self.assertEqual(last_entry.state, queue.EntryState.ADDED)

        # First item should be the initial item, with EntryState.REMOVED
        self.assertEqual(first_entry.priority, 1)
        self.assertEqual(first_entry.p_item, initial_item)
        self.assertEqual(first_entry.state, queue.EntryState.REMOVED)

        # Item in entry_finder should be the updated item
        item = self.pq.entry_finder[self.pq.get_item_identifier(updated_item.item)]
        self.assertEqual(item.priority, updated_item.priority)
        self.assertEqual(item.p_item, updated_item)
        self.assertEqual(item.state, queue.EntryState.ADDED)

        # When popping off the queue you should end up with the updated_item
        # that now has the lowest priority.
        popped_item = self.pq.pop()
        self.assertEqual(popped_item, updated_item)

        # The queue should now have 1 item, because the removed item was
        # discarded while popping
        self.assertEqual(len(self.pq), 0)
        self.assertEqual(len(self.pq.entry_finder), 0)

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

        first_entry = self.pq.peek(0)

        # First item should be the item with EntryState.REMOVED
        self.assertEqual(first_entry.priority, 1)
        self.assertEqual(first_entry.p_item, item)
        self.assertEqual(first_entry.state, queue.EntryState.REMOVED)

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

    # TODO: Add tests for the following methods
    def test_maxsize(self):
        pass
