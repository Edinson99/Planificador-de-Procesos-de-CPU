import json
import tempfile
import unittest
from pathlib import Path

from src.engine.simulator import SimulationSnapshot, Simulator
from src.models.process import IOEvent, Process
from src.process_io import load_processes_file, save_processes_file
from src.schedulers import (
    FCFSScheduler,
    PreemptivePriorityScheduler,
    SRTFScheduler,
)


class AdvancedSimulationTests(unittest.TestCase):
    def test_srtf_preempts_for_shorter_remaining_time(self) -> None:
        processes = [
            Process("P1", 0, 7),
            Process("P2", 2, 4),
            Process("P3", 4, 1),
        ]

        result = Simulator(SRTFScheduler()).run(processes)

        self.assertEqual(
            [(segment.start, segment.end, segment.pid) for segment in result.gantt],
            [
                (0, 2, "P1"),
                (2, 4, "P2"),
                (4, 5, "P3"),
                (5, 7, "P2"),
                (7, 12, "P1"),
            ],
        )
        self.assertEqual([process.waiting_time for process in processes], [5, 1, 0])

    def test_preemptive_priority_switches_to_higher_priority_process(self) -> None:
        processes = [
            Process("P1", 0, 5, priority=3),
            Process("P2", 2, 2, priority=1),
        ]

        result = Simulator(PreemptivePriorityScheduler()).run(processes)

        self.assertEqual(
            [(segment.start, segment.end, segment.pid) for segment in result.gantt],
            [(0, 2, "P1"), (2, 4, "P2"), (4, 7, "P1")],
        )
        self.assertEqual(result.context_switches, 2)

    def test_multiple_io_events_block_and_resume_process(self) -> None:
        process = Process(
            "P1",
            0,
            5,
            io_events=[IOEvent(after_cpu=1, duration=2), IOEvent(after_cpu=3, duration=1)],
        )

        result = Simulator(FCFSScheduler()).run([process])

        self.assertEqual(
            [(segment.start, segment.end, segment.pid) for segment in result.gantt],
            [
                (0, 1, "P1"),
                (1, 3, None),
                (3, 5, "P1"),
                (5, 6, None),
                (6, 8, "P1"),
            ],
        )
        self.assertEqual(process.turnaround_time, 8)
        self.assertEqual(process.blocked_time, 3)
        self.assertEqual(process.waiting_time, 0)
        self.assertEqual(len(result.timeline), result.makespan + 1)

    def test_snapshot_captures_ready_running_and_blocked_queues(self) -> None:
        processes = [
            Process("P1", 0, 3, io_after=1, io_duration=2),
            Process("P2", 0, 2),
        ]

        result = Simulator(FCFSScheduler()).run(processes)

        self.assertIsInstance(result.timeline[0], SimulationSnapshot)
        self.assertEqual(result.timeline[0].running, "P1")
        self.assertEqual(result.timeline[0].ready, ("P2",))
        self.assertEqual(result.timeline[1].running, "P2")
        self.assertEqual(result.timeline[1].blocked, ("P1",))
        self.assertEqual(result.timeline[-1].terminated, ("P1", "P2"))

    def test_arrival_is_queued_before_process_unblocked_at_same_tick(self) -> None:
        processes = [
            Process("P1", 0, 2, io_after=1, io_duration=1),
            Process("P2", 2, 1),
        ]

        result = Simulator(FCFSScheduler()).run(processes)

        self.assertEqual(result.timeline[2].running, "P2")
        self.assertEqual(result.timeline[2].ready, ("P1",))

    def test_cpu_utilization_throughput_and_context_switches(self) -> None:
        processes = [Process("P1", 0, 2), Process("P2", 0, 1)]

        result = Simulator(FCFSScheduler()).run(processes)

        self.assertEqual(result.cpu_busy_time, 3)
        self.assertEqual(result.cpu_idle_time, 0)
        self.assertEqual(result.cpu_utilization, 100.0)
        self.assertAlmostEqual(result.throughput, 2 / 3)
        self.assertEqual(result.context_switches, 1)

    def test_idle_ticks_are_included_in_utilization_denominator(self) -> None:
        result = Simulator(FCFSScheduler()).run([Process("P1", 2, 1)])

        self.assertEqual(result.cpu_idle_time, 2)
        self.assertEqual(result.cpu_busy_time, 1)
        self.assertAlmostEqual(result.cpu_utilization, 100 / 3)
        self.assertAlmostEqual(result.throughput, 1 / 3)

    def test_json_round_trip_and_legacy_io_format(self) -> None:
        processes = [
            Process(
                "P1",
                1,
                6,
                priority=2,
                io_events=[IOEvent(2, 3), IOEvent(4, 1)],
            )
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scenario.json"
            save_processes_file(path, processes)
            loaded = load_processes_file(path)

            self.assertEqual(loaded[0].pid, "P1")
            self.assertEqual(loaded[0].io_events, processes[0].io_events)

            legacy_path = Path(directory) / "legacy.json"
            legacy_path.write_text(
                json.dumps(
                    [
                        {
                            "pid": "P2",
                            "arrival_time": 0,
                            "burst_time": 4,
                            "io_after": 1,
                            "io_duration": 2,
                        }
                    ]
                ),
                encoding="utf-8",
            )
            legacy_loaded = load_processes_file(legacy_path)
            self.assertEqual(legacy_loaded[0].io_events, [IOEvent(1, 2)])


if __name__ == "__main__":
    unittest.main()
