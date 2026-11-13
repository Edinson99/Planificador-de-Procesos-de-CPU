import unittest

from src.engine.simulator import Simulator
from src.models.process import IOEvent, Process
from src.schedulers import FCFSScheduler
from src.ui.app import SchedulerApp, _statistics


class GuiLogicTests(unittest.TestCase):
    def test_statistics_returns_min_mean_max_and_population_deviation(self) -> None:
        self.assertEqual(_statistics([0, 2]), (0, 1.0, 2, 1.0))

    def test_io_entry_parser_supports_multiple_events(self) -> None:
        self.assertEqual(
            SchedulerApp._parse_io_events("1:2, 4:3"),
            [IOEvent(1, 2), IOEvent(4, 3)],
        )
        with self.assertRaises(ValueError):
            SchedulerApp._parse_io_events("4:2, 1:3")

    def test_process_state_rows_include_ready_running_and_blocked_intervals(self) -> None:
        processes = [
            Process("P1", 0, 3, io_after=1, io_duration=2),
            Process("P2", 0, 2),
        ]
        result = Simulator(FCFSScheduler()).run(processes)
        p1 = result.processes[0]
        running_by_tick = [None] * result.makespan
        for segment in result.gantt:
            for tick in range(segment.start, segment.end):
                running_by_tick[tick] = segment.pid

        states = SchedulerApp._process_states(p1, result, running_by_tick)

        self.assertEqual(
            SchedulerApp._state_intervals(states),
            [("Ejecucion", 0, 1), ("Bloqueado", 1, 3), ("Ejecucion", 3, 5)],
        )

    def test_process_state_rows_show_multiple_block_periods(self) -> None:
        process = Process(
            "P1",
            0,
            5,
            io_events=[IOEvent(1, 2), IOEvent(3, 1)],
        )
        result = Simulator(FCFSScheduler()).run([process])
        running_by_tick = [None] * result.makespan
        for segment in result.gantt:
            for tick in range(segment.start, segment.end):
                running_by_tick[tick] = segment.pid

        states = SchedulerApp._process_states(process, result, running_by_tick)

        self.assertEqual(
            SchedulerApp._state_intervals(states),
            [
                ("Ejecucion", 0, 1),
                ("Bloqueado", 1, 3),
                ("Ejecucion", 3, 5),
                ("Bloqueado", 5, 6),
                ("Ejecucion", 6, 8),
            ],
        )


if __name__ == "__main__":
    unittest.main()
