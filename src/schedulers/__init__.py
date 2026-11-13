from src.schedulers.fcfs import FCFSScheduler
from src.schedulers.preemptive_priority import PreemptivePriorityScheduler
from src.schedulers.priority import PriorityScheduler
from src.schedulers.round_robin import RoundRobinScheduler
from src.schedulers.sjf import SJFScheduler
from src.schedulers.srtf import SRTFScheduler
from src.schedulers.base import Scheduler


def create_scheduler(name: str, quantum: int = 2) -> Scheduler:
    schedulers = {
        "fcfs": FCFSScheduler,
        "sjf": SJFScheduler,
        "srtf": SRTFScheduler,
        "rr": lambda: RoundRobinScheduler(quantum),
        "priority": PriorityScheduler,
        "priority_preemptive": PreemptivePriorityScheduler,
    }
    try:
        return schedulers[name]()
    except KeyError as error:
        raise ValueError("Algoritmo desconocido: {}.".format(name)) from error

__all__ = [
    "FCFSScheduler",
    "PreemptivePriorityScheduler",
    "PriorityScheduler",
    "RoundRobinScheduler",
    "SRTFScheduler",
    "Scheduler",
    "SJFScheduler",
    "create_scheduler",
]
