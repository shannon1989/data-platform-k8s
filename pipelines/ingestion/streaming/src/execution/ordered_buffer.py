from ../control/range_record import RangeRecord

# OrderedResultBuffer（保证顺序提交）- ingestion 的灵魂组件
# 介于 RPC 与 Kafka 之间
# 不关心 retry / planner

class OrderedResultBuffer:
    def __init__(self):
        self._buffer = {}
        self._next_range_id = 0

    def add(self, result: RangeRecord):
        self._buffer[result.range_id] = result

    def pop_ready(self):
        ready = []
        while self._next_range_id in self._buffer:
            ready.append(self._buffer.pop(self._next_range_id))
            self._next_range_id += 1
        return ready