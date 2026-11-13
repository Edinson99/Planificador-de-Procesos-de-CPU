const ALGORITHMS = new Set([
  "fcfs",
  "sjf",
  "srtf",
  "rr",
  "priority",
  "priority_preemptive",
]);

function validateProcesses(input) {
  if (!Array.isArray(input) || input.length === 0) {
    throw new Error("Debe proporcionarse al menos un proceso.");
  }

  const seen = new Set();
  return input.map((item) => {
    if (!item || typeof item.pid !== "string" || !item.pid.trim()) {
      throw new Error("El PID no puede estar vacío.");
    }
    if (seen.has(item.pid)) {
      throw new Error("Los PID de los procesos deben ser únicos.");
    }
    seen.add(item.pid);

    for (const [field, label, min] of [
      ["arrival_time", "El tiempo de llegada", 0],
      ["burst_time", "La ráfaga de CPU", 1],
    ]) {
      if (!Number.isSafeInteger(item[field]) || item[field] < min) {
        throw new Error(`${label} debe ser un entero ${min === 0 ? "no negativo" : "mayor que cero"}.`);
      }
    }
    const priority = item.priority ?? 0;
    if (!Number.isSafeInteger(priority)) {
      throw new Error("La prioridad debe ser un entero.");
    }

    let ioEvents = item.io_events ?? [];
    if (!Array.isArray(ioEvents)) {
      throw new Error("Los eventos de E/S deben ser una lista.");
    }
    if (item.io_after !== undefined || item.io_duration !== undefined) {
      if (item.io_after === undefined || item.io_duration === undefined || ioEvents.length) {
        throw new Error("Usa io_events o io_after/io_duration, pero no ambos.");
      }
      ioEvents = [{ after_cpu: item.io_after, duration: item.io_duration }];
    }

    let previousAfterCpu = 0;
    ioEvents = ioEvents.map((event) => {
      if (!Number.isSafeInteger(event?.after_cpu) || event.after_cpu <= previousAfterCpu) {
        throw new Error("Los eventos de E/S deben tener after_cpu positivo y estar ordenados sin repetirse.");
      }
      if (event.after_cpu >= item.burst_time) {
        throw new Error("after_cpu debe ser menor que la ráfaga total de CPU.");
      }
      if (!Number.isSafeInteger(event.duration) || event.duration <= 0) {
        throw new Error("La duración de E/S debe ser un entero mayor que cero.");
      }
      previousAfterCpu = event.after_cpu;
      return { after_cpu: event.after_cpu, duration: event.duration };
    });

    return {
      pid: item.pid,
      arrival_time: item.arrival_time,
      burst_time: item.burst_time,
      priority,
      io_events: ioEvents,
      remaining_time: item.burst_time,
      state: "new",
      first_start_time: null,
      completion_time: null,
    };
  });
}

function chooseNext(ready, algorithm) {
  if (algorithm === "fcfs" || algorithm === "rr") {
    return ready.shift();
  }
  const score = (process) => {
    if (algorithm === "sjf") return [process.burst_time, process.arrival_time];
    if (algorithm === "srtf") return [process.remaining_time, process.arrival_time];
    return [process.priority, process.arrival_time];
  };
  let bestIndex = 0;
  for (let index = 1; index < ready.length; index += 1) {
    const candidate = score(ready[index]);
    const best = score(ready[bestIndex]);
    if (candidate[0] < best[0] || (candidate[0] === best[0] && candidate[1] < best[1])) {
      bestIndex = index;
    }
  }
  return ready.splice(bestIndex, 1)[0];
}

function shouldPreempt(current, ready, algorithm) {
  if (algorithm === "srtf") {
    return ready.some((process) => process.remaining_time < current.remaining_time);
  }
  if (algorithm === "priority_preemptive") {
    return ready.some((process) => process.priority < current.priority);
  }
  return false;
}

function recordTick(gantt, time, pid) {
  const previous = gantt[gantt.length - 1];
  if (previous && previous.pid === pid) {
    previous.end = time + 1;
  } else {
    gantt.push({ start: time, end: time + 1, pid });
  }
}

export function runSimulation(input, algorithm = "fcfs", quantum = 2) {
  if (!ALGORITHMS.has(algorithm)) {
    throw new Error("Selecciona un algoritmo válido.");
  }
  if (algorithm === "rr" && (!Number.isSafeInteger(quantum) || quantum <= 0)) {
    throw new Error("El quantum debe ser un entero mayor que cero.");
  }

  const processes = validateProcesses(input);
  const ready = [];
  const blockedUntil = new Map();
  const nextIoEvent = new Map(processes.map((process) => [process.pid, 0]));
  const gantt = [];
  const timeline = [];
  let current = null;
  let quantumLeft = null;
  let time = 0;

  while (processes.some((process) => process.state !== "terminated")) {
    for (const process of processes) {
      if (process.state === "new" && process.arrival_time <= time) {
        process.state = "ready";
        ready.push(process);
      }
    }
    for (const process of processes) {
      if (process.state === "blocked" && blockedUntil.get(process.pid) <= time) {
        process.state = "ready";
        ready.push(process);
      }
    }

    if (current && ready.length && shouldPreempt(current, ready, algorithm)) {
      current.state = "ready";
      ready.push(current);
      current = null;
      quantumLeft = null;
    }
    if (!current && ready.length) {
      current = chooseNext(ready, algorithm);
      current.state = "running";
      if (current.first_start_time === null) current.first_start_time = time;
      quantumLeft = algorithm === "rr" ? quantum : null;
    }

    timeline.push({
      time,
      running: current?.pid ?? null,
      ready: ready.map((process) => process.pid),
      blocked: processes.filter((process) => process.state === "blocked").map((process) => process.pid),
      new: processes.filter((process) => process.state === "new").map((process) => process.pid),
      terminated: processes.filter((process) => process.state === "terminated").map((process) => process.pid),
    });

    if (!current) {
      recordTick(gantt, time, null);
      time += 1;
      continue;
    }

    recordTick(gantt, time, current.pid);
    current.remaining_time -= 1;
    time += 1;
    if (quantumLeft !== null) quantumLeft -= 1;

    if (current.remaining_time === 0) {
      current.completion_time = time;
      current.state = "terminated";
      current = null;
      quantumLeft = null;
    } else {
      const eventIndex = nextIoEvent.get(current.pid);
      const event = current.io_events[eventIndex];
      if (event && current.burst_time - current.remaining_time === event.after_cpu) {
        current.state = "blocked";
        blockedUntil.set(current.pid, time + event.duration);
        nextIoEvent.set(current.pid, eventIndex + 1);
        current = null;
        quantumLeft = null;
      } else if (quantumLeft === 0) {
        current.state = "ready";
        ready.push(current);
        current = null;
        quantumLeft = null;
      }
    }
  }

  timeline.push({
    time,
    running: null,
    ready: ready.map((process) => process.pid),
    blocked: processes.filter((process) => process.state === "blocked").map((process) => process.pid),
    new: processes.filter((process) => process.state === "new").map((process) => process.pid),
    terminated: processes.filter((process) => process.state === "terminated").map((process) => process.pid),
  });

  const makespan = gantt.at(-1)?.end ?? 0;
  const cpuBusyTime = gantt.reduce(
    (total, segment) => total + (segment.pid === null ? 0 : segment.end - segment.start),
    0,
  );
  const completed = processes.map((process) => ({
    ...process,
    turnaround_time: process.completion_time - process.arrival_time,
    waiting_time: process.completion_time - process.arrival_time - process.burst_time
      - process.io_events.reduce((total, event) => total + event.duration, 0),
    response_time: process.first_start_time - process.arrival_time,
    blocked_time: process.io_events.reduce((total, event) => total + event.duration, 0),
  }));
  let contextSwitches = 0;
  let previousPid = null;
  for (const segment of gantt) {
    if (previousPid !== null && segment.pid !== null && segment.pid !== previousPid) {
      contextSwitches += 1;
    }
    previousPid = segment.pid;
  }

  return {
    processes: completed,
    gantt,
    timeline,
    makespan,
    cpuBusyTime,
    cpuIdleTime: makespan - cpuBusyTime,
    cpuUtilization: makespan === 0 ? 0 : (cpuBusyTime / makespan) * 100,
    throughput: makespan === 0 ? 0 : processes.length / makespan,
    averageWaitingTime: completed.reduce((sum, process) => sum + process.waiting_time, 0) / completed.length,
    averageTurnaroundTime: completed.reduce((sum, process) => sum + process.turnaround_time, 0) / completed.length,
    contextSwitches,
  };
}
