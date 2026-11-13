from typing import List

from src.models.process import Process
from src.schedulers.base import Scheduler


class PriorityScheduler(Scheduler):
    def select_next(self, ready: List[Process]) -> Process:
        index = min(
            range(len(ready)),
            key=lambda item: (
                ready[item].priority,
                ready[item].arrival_time,
            ),
        )
        return ready.pop(index)
