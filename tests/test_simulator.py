import unittest

from src.engine.simulator import Simulator
from src.models.process import Process, ProcessState
from src.schedulers import (
    FCFSScheduler,
    PriorityScheduler,
    RoundRobinScheduler,
    SJFScheduler,
)


class SimulatorTests(unittest.TestCase):
    def test_fcfs_calculates_waiting_and_turnaround(self) -> None:
        processes = [
            Process("P1", 0, 5),
            Process("P2", 1, 3),
            Process("P3", 2, 1),
        ]

        result = Simulator(FCFSScheduler()).run(processes)

        self.assertEqual([p.completion_time for p in processes], [5, 8, 9])
        self.assertEqual([p.waiting_time for p in processes], [0, 4, 6])
        self.assertEqual([p.turnaround_time for p in processes], [5, 7, 7])
        self.assertEqual(result.average_waiting_time, 10 / 3)
        self.assertEqual(
            [(part.start, part.end, part.pid) for part in result.gantt],
            [(0, 5, "P1"), (5, 8, "P2"), (8, 9, "P3")],
        )

    def test_sjf_selects_shortest_ready_process(self) -> None:
        processes = [
            Process("P1", 0, 7),
            Process("P2", 2, 4),
            Process("P3", 4, 1),
        ]

        Simulator(SJFScheduler()).run(processes)

        self.assertEqual([p.completion_time for p in processes], [7, 12, 8])
        self.assertEqual([p.waiting_time for p in processes], [0, 6, 3])

    def test_round_robin_requeues_after_quantum(self) -> None:
        processes = [Process("P1", 0, 5), Process("P2", 1, 3)]

        result = Simulator(RoundRobinScheduler(2)).run(processes)

        self.assertEqual([p.completion_time for p in processes], [8, 7])
        self.assertEqual([p.waiting_time for p in processes], [3, 3])
        self.assertEqual(
            [(part.start, part.end, part.pid) for part in result.gantt],
            [
                (0, 2, "P1"),
                (2, 4, "P2"),
                (4, 6, "P1"),
                (6, 7, "P2"),
                (7, 8, "P1"),
            ],
        )

    def test_priority_uses_lowest_value_first(self) -> None:
        processes = [
            Process("P1", 0, 4, priority=3),
            Process("P2", 0, 2, priority=1),
        ]

        result = Simulator(PriorityScheduler()).run(processes)

        self.assertEqual([part.pid for part in result.gantt], ["P2", "P1"])

    def test_io_moves_process_through_blocked_state(self) -> None:
        processes = [
            Process("P1", 0, 3, io_after=1, io_duration=2),
            Process("P2", 0, 2),
        ]

        result = Simulator(FCFSScheduler()).run(processes)

        self.assertEqual([p.completion_time for p in processes], [5, 3])
        self.assertEqual([p.waiting_time for p in processes], [0, 1])
        self.assertEqual(
            [(part.start, part.end, part.pid) for part in result.gantt],
            [(0, 1, "P1"), (1, 3, "P2"), (3, 5, "P1")],
        )
        self.assertTrue(
            all(process.state is ProcessState.TERMINATED for process in processes)
        )

    def test_rejects_invalid_state_transition(self) -> None:
        process = Process("P1", 0, 1)

        with self.assertRaises(ValueError):
            process.transition_to(ProcessState.RUNNING)


if __name__ == "__main__":
    unittest.main()
