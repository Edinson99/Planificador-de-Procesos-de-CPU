import assert from "node:assert/strict";
import test from "node:test";

import { runSimulation } from "./simulator.mjs";

test("FCFS calcula Gantt, métricas y tiempos por proceso", () => {
  const result = runSimulation([
    { pid: "P1", arrival_time: 0, burst_time: 5 },
    { pid: "P2", arrival_time: 1, burst_time: 3 },
    { pid: "P3", arrival_time: 2, burst_time: 1 },
  ]);

  assert.deepEqual(result.gantt, [
    { start: 0, end: 5, pid: "P1" },
    { start: 5, end: 8, pid: "P2" },
    { start: 8, end: 9, pid: "P3" },
  ]);
  assert.deepEqual(result.processes.map((process) => process.waiting_time), [0, 4, 6]);
  assert.equal(result.averageWaitingTime, 10 / 3);
  assert.equal(result.contextSwitches, 2);
});

test("SRTF expropia por menor tiempo restante", () => {
  const result = runSimulation([
    { pid: "P1", arrival_time: 0, burst_time: 7 },
    { pid: "P2", arrival_time: 2, burst_time: 4 },
    { pid: "P3", arrival_time: 4, burst_time: 1 },
  ], "srtf");

  assert.deepEqual(result.gantt.map(({ start, end, pid }) => [start, end, pid]), [
    [0, 2, "P1"],
    [2, 4, "P2"],
    [4, 5, "P3"],
    [5, 7, "P2"],
    [7, 12, "P1"],
  ]);
  assert.deepEqual(result.processes.map((process) => process.waiting_time), [5, 1, 0]);
});

test("E/S múltiple refleja bloqueos, ticks y métricas", () => {
  const result = runSimulation([{
    pid: "P1",
    arrival_time: 0,
    burst_time: 5,
    io_events: [{ after_cpu: 1, duration: 2 }, { after_cpu: 3, duration: 1 }],
  }]);

  assert.deepEqual(result.gantt.map(({ start, end, pid }) => [start, end, pid]), [
    [0, 1, "P1"],
    [1, 3, null],
    [3, 5, "P1"],
    [5, 6, null],
    [6, 8, "P1"],
  ]);
  assert.equal(result.timeline.length, result.makespan + 1);
  assert.equal(result.processes[0].waiting_time, 0);
});

test("Round Robin valida el quantum y reencola procesos", () => {
  const input = [
    { pid: "P1", arrival_time: 0, burst_time: 5 },
    { pid: "P2", arrival_time: 1, burst_time: 3 },
  ];
  assert.throws(() => runSimulation(input, "rr", 0), /quantum/i);
  const result = runSimulation(input, "rr", 2);
  assert.deepEqual(result.gantt.map(({ start, end, pid }) => [start, end, pid]), [
    [0, 2, "P1"],
    [2, 4, "P2"],
    [4, 6, "P1"],
    [6, 7, "P2"],
    [7, 8, "P1"],
  ]);
});

test("Prioridad preemptiva cambia a la llegada de una prioridad mayor", () => {
  const input = [
    { pid: "P1", arrival_time: 0, burst_time: 5, priority: 3 },
    { pid: "P2", arrival_time: 2, burst_time: 2, priority: 1 },
  ];
  const result = runSimulation(input, "priority_preemptive");

  assert.deepEqual(result.gantt.map(({ start, end, pid }) => [start, end, pid]), [
    [0, 2, "P1"],
    [2, 4, "P2"],
    [4, 7, "P1"],
  ]);
});

test("rechaza datos que no serían aceptados por el simulador Python", () => {
  assert.throws(() => runSimulation([
    { pid: "P1", arrival_time: 0, burst_time: 3, io_events: [{ after_cpu: 3, duration: 1 }] },
  ]), /menor que la ráfaga/);
  assert.throws(() => runSimulation([
    { pid: "P1", arrival_time: 0, burst_time: 2 },
    { pid: "P1", arrival_time: 1, burst_time: 1 },
  ]), /únicos/);
});
