import { runSimulation } from "./simulator.mjs";

const processList = document.querySelector("#process-list");
const algorithmSelect = document.querySelector("#algorithm");
const quantumField = document.querySelector("#quantum-field");
const resultsSection = document.querySelector("#results");
const errorMessage = document.querySelector("#error-message");
const timelineInput = document.querySelector("#timeline");
let nextPid = 1;
let currentResult = null;
let playbackTimer = null;

function createProcessRow(process = {}) {
  const row = document.createElement("tr");
  const pid = process.pid ?? `P${nextPid++}`;
  const pidNumber = /^P(\d+)$/i.exec(pid);
  if (pidNumber) nextPid = Math.max(nextPid, Number(pidNumber[1]) + 1);
  const fields = [
    ["pid", pid, "text"],
    ["arrival_time", process.arrival_time ?? 0, "number"],
    ["burst_time", process.burst_time ?? 5, "number"],
    ["priority", process.priority ?? 0, "number"],
    ["io_events", (process.io_events ?? []).map((event) => `${event.after_cpu}:${event.duration}`).join(", "), "text"],
  ];
  for (const [name, value, type] of fields) {
    const cell = document.createElement("td");
    const input = document.createElement("input");
    input.name = name;
    input.type = type;
    input.value = value;
    input.setAttribute("aria-label", name.replace("_", " "));
    if (type === "number") {
      input.step = "1";
      if (name !== "priority") input.min = "0";
      if (name === "burst_time") input.min = "1";
    }
    if (name === "io_events") input.placeholder = "2:3, 5:1";
    cell.append(input);
    row.append(cell);
  }
  const actionCell = document.createElement("td");
  const removeButton = document.createElement("button");
  removeButton.type = "button";
  removeButton.className = "button button-secondary button-remove";
  removeButton.textContent = "Quitar";
  removeButton.setAttribute("aria-label", `Quitar ${pid}`);
  removeButton.addEventListener("click", () => row.remove());
  actionCell.append(removeButton);
  row.append(actionCell);
  processList.append(row);
}

function parseInteger(value, label) {
  if (value.trim() === "") throw new Error(`${label} es obligatorio.`);
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed)) throw new Error(`${label} debe ser un entero.`);
  return parsed;
}

function readProcesses() {
  return [...processList.rows].map((row, index) => {
    const value = (name) => row.querySelector(`[name="${name}"]`).value;
    const ioText = value("io_events").trim();
    const ioEvents = ioText
      ? ioText.split(",").map((part) => {
        const match = part.trim().match(/^(\d+)\s*:\s*(\d+)$/);
        if (!match) throw new Error(`Formato de E/S inválido en el proceso ${index + 1}. Usa after_cpu:duración.`);
        return { after_cpu: Number(match[1]), duration: Number(match[2]) };
      })
      : [];
    return {
      pid: value("pid").trim(),
      arrival_time: parseInteger(value("arrival_time"), "Llegada"),
      burst_time: parseInteger(value("burst_time"), "Ráfaga"),
      priority: parseInteger(value("priority"), "Prioridad"),
      io_events: ioEvents,
    };
  });
}

function colorForPid(pid) {
  let hash = 0;
  for (const character of pid) hash = ((hash << 5) - hash + character.charCodeAt(0)) | 0;
  const colors = ["#2365aa", "#6a4ca5", "#208273", "#a65b20", "#b4405b", "#466b3c"];
  return colors[Math.abs(hash) % colors.length];
}

function showGantt() {
  const container = document.querySelector("#gantt");
  container.replaceChildren();
  const track = document.createElement("div");
  track.className = "gantt-track";
  for (const segment of currentResult.gantt) {
    const element = document.createElement("button");
    element.type = "button";
    element.className = `gantt-segment${segment.pid === null ? " idle" : ""}`;
    element.dataset.start = String(segment.start);
    element.style.width = `${Math.max(72, (segment.end - segment.start) * 54)}px`;
    if (segment.pid !== null) element.style.backgroundColor = colorForPid(segment.pid);
    const processLabel = document.createElement("span");
    processLabel.textContent = segment.pid ?? "Libre";
    const timeLabel = document.createElement("small");
    timeLabel.textContent = `${segment.start}–${segment.end}`;
    element.append(processLabel, timeLabel);
    element.addEventListener("click", () => {
      timelineInput.value = String(segment.start);
      updateTimeline();
    });
    track.append(element);
  }
  container.append(track);
  updateTimeline();
}

function showMetrics() {
  const metrics = [
    ["Espera promedio", `${currentResult.averageWaitingTime.toFixed(2)} ticks`],
    ["Retorno promedio", `${currentResult.averageTurnaroundTime.toFixed(2)} ticks`],
    ["Utilización CPU", `${currentResult.cpuUtilization.toFixed(2)}%`],
    ["Rendimiento", `${currentResult.throughput.toFixed(4)} procesos/tick`],
    ["Tiempo libre", `${currentResult.cpuIdleTime} ticks`],
    ["Cambios de contexto", String(currentResult.contextSwitches)],
  ];
  const container = document.querySelector("#metrics");
  container.replaceChildren();
  for (const [label, value] of metrics) {
    const card = document.createElement("div");
    card.className = "metric-card";
    const name = document.createElement("span");
    name.textContent = label;
    const result = document.createElement("strong");
    result.textContent = value;
    card.append(name, result);
    container.append(card);
  }

  const body = document.querySelector("#process-results");
  body.replaceChildren();
  for (const process of currentResult.processes) {
    const row = document.createElement("tr");
    for (const value of [
      process.pid,
      process.arrival_time,
      process.burst_time,
      process.first_start_time,
      process.completion_time,
      process.turnaround_time,
      process.waiting_time,
      process.response_time,
    ]) {
      const cell = document.createElement("td");
      cell.textContent = String(value);
      row.append(cell);
    }
    body.append(row);
  }
}

function updateTimeline() {
  if (!currentResult) return;
  const tick = Number(timelineInput.value);
  document.querySelector("#tick-label").textContent = String(tick);
  const snapshot = currentResult.timeline[tick];
  const groups = [
    ["En ejecución", snapshot.running ? [snapshot.running] : []],
    ["Listos", snapshot.ready],
    ["Bloqueados", snapshot.blocked],
    ["Nuevos", snapshot.new],
    ["Terminados", snapshot.terminated],
  ];
  const container = document.querySelector("#snapshot");
  container.replaceChildren();
  for (const [label, processes] of groups) {
    const card = document.createElement("div");
    card.className = "state-card";
    const heading = document.createElement("strong");
    heading.textContent = label;
    const content = document.createElement("span");
    content.textContent = processes.length ? processes.join(", ") : "—";
    card.append(heading, content);
    container.append(card);
  }
  for (const segment of document.querySelectorAll(".gantt-segment")) {
    const start = Number(segment.dataset.start);
    const end = currentResult.gantt.find((item) => item.start === start).end;
    segment.classList.toggle("selected", tick >= start && tick < end);
  }
}

function stopPlayback() {
  if (playbackTimer !== null) {
    window.clearInterval(playbackTimer);
    playbackTimer = null;
  }
  document.querySelector("#playback").textContent = "Reproducir";
}

function run() {
  try {
    stopPlayback();
    errorMessage.hidden = true;
    currentResult = runSimulation(
      readProcesses(),
      algorithmSelect.value,
      parseInteger(document.querySelector("#quantum").value, "Quantum"),
    );
    timelineInput.min = "0";
    timelineInput.max = String(currentResult.makespan);
    timelineInput.value = "0";
    resultsSection.hidden = false;
    showGantt();
    showMetrics();
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
  }
}

document.querySelector("#add-process").addEventListener("click", () => createProcessRow());
document.querySelector("#run-simulation").addEventListener("click", run);
document.querySelector("#algorithm").addEventListener("change", () => {
  quantumField.hidden = algorithmSelect.value !== "rr";
});
document.querySelector("#previous-tick").addEventListener("click", () => {
  timelineInput.value = String(Math.max(0, Number(timelineInput.value) - 1));
  updateTimeline();
});
document.querySelector("#next-tick").addEventListener("click", () => {
  timelineInput.value = String(Math.min(currentResult.makespan, Number(timelineInput.value) + 1));
  updateTimeline();
});
timelineInput.addEventListener("input", updateTimeline);
document.querySelector("#playback").addEventListener("click", () => {
  if (playbackTimer !== null) {
    stopPlayback();
    return;
  }
  if (Number(timelineInput.value) >= currentResult.makespan) timelineInput.value = "0";
  document.querySelector("#playback").textContent = "Pausar";
  playbackTimer = window.setInterval(() => {
    const nextTick = Number(timelineInput.value) + 1;
    timelineInput.value = String(nextTick);
    updateTimeline();
    if (nextTick >= currentResult.makespan) stopPlayback();
  }, 650);
});

document.querySelector("#load-example").addEventListener("click", () => {
  processList.replaceChildren();
  nextPid = 1;
  createProcessRow({ pid: "P1", arrival_time: 0, burst_time: 5, priority: 2 });
  createProcessRow({ pid: "P2", arrival_time: 1, burst_time: 3, priority: 1 });
  createProcessRow({ pid: "P3", arrival_time: 2, burst_time: 1, priority: 3 });
  algorithmSelect.value = "fcfs";
  quantumField.hidden = true;
  run();
});

document.querySelector("#import-button").addEventListener("click", () => {
  document.querySelector("#import-file").click();
});
document.querySelector("#import-file").addEventListener("change", async (event) => {
  const [file] = event.target.files;
  if (!file) return;
  try {
    const processes = JSON.parse(await file.text());
    if (!Array.isArray(processes)) throw new Error("El escenario debe ser una lista JSON de procesos.");
    processList.replaceChildren();
    nextPid = 1;
    for (const process of processes) {
      const events = process.io_events
        ?? (process.io_after !== undefined && process.io_duration !== undefined
          ? [{ after_cpu: process.io_after, duration: process.io_duration }]
          : []);
      createProcessRow({ ...process, io_events: events });
    }
    errorMessage.hidden = true;
  } catch (error) {
    errorMessage.textContent = `No se pudo importar el escenario: ${error.message}`;
    errorMessage.hidden = false;
  } finally {
    event.target.value = "";
  }
});
document.querySelector("#export-button").addEventListener("click", () => {
  try {
    const json = JSON.stringify(readProcesses(), null, 2);
    const url = URL.createObjectURL(new Blob([json], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = "escenario-cpu.json";
    link.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    errorMessage.textContent = error.message;
    errorMessage.hidden = false;
  }
});

createProcessRow({ pid: "P1", arrival_time: 0, burst_time: 5, priority: 2 });
createProcessRow({ pid: "P2", arrival_time: 1, burst_time: 3, priority: 1 });
createProcessRow({ pid: "P3", arrival_time: 2, burst_time: 1, priority: 3 });
