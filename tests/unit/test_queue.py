import copy
import unittest
import uuid

import pydantic
from scheduler import queue


class TestModel(pydantic.BaseModel):
    id: str = uuid.uuid4().hex
    name: str

    def __hash__(self):
        return hash((self.id, self.name))


class PriorityQueueTestCase(unittest.TestCase):
    def setUp(self):

        self.pq = queue.PriorityQueue(
            id="test-queue",
            maxsize=10,
            item_type=TestModel,
        )

        self.item0 = queue.PrioritizedItem(
            priority=1,
            item=TestModel(name="test"),
        )

    def test_push(self):
        self.pq.push(p_item=self.item0)
        self.assertEqual(len(self.pq), 1)
        self.assertEqual(len(self.pq.entry_finder), 1)

    def test_push_update(self):
        """When updating an initial item on the priority queue, the updated
        item should be added to the queue, the initial item should be marked as
        removed, and the iniital removed from the entry_finder.
        """
        self.pq.push(p_item=self.item0)

        updated_item = copy.deepcopy(self.item0)
        updated_item.priority = 2

        self.pq.push(p_item=updated_item)

        self.assertEqual(len(self.pq), 2)
        self.assertEqual(len(self.pq.entry_finder), 1)

        # Last item should be an item with EntryState.REMOVED
        last_item = self.pq.peek(-1)
        print("last_item: ", last_item)

        # TODO: check EntryState to be set to remove
        removed_item = self.pq.pop()

        print(self.pq.entry_finder)

    def test_push_duplicate(self):
        pass

    def test_pop(self):
        pass

    def test_test(self):
        pass
