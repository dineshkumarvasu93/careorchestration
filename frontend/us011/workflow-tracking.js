const apiBase = "http://localhost:8000";

const form = document.getElementById("tracking-form");
const runInput = document.getElementById("run-id");
const statusLine = document.getElementById("status-line");

const sumRun = document.getElementById("sum-run");
const sumPatient = document.getElementById("sum-patient");
const sumRunStatus = document.getElementById("sum-run-status");
const sumTaskCount = document.getElementById("sum-task-count");
const sumEscalations = document.getElementById("sum-escalations");

const taskEmpty = document.getElementById("task-empty");
const taskTable = document.getElementById("task-table");
const taskBody = document.getElementById("task-body");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const runId = runInput.value.trim();
  if (!runId) {
    statusLine.textContent = "Run ID is required.";
    return;
  }

  statusLine.textContent = `Loading tracking for ${runId}...`;
  try {
    const response = await fetch(`${apiBase}/api/v1/orchestration/runs/${encodeURIComponent(runId)}/tracking`);
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }

    const payload = await response.json();
    renderTracking(payload);
    statusLine.textContent = `Loaded tracking for ${runId}.`;
  } catch (error) {
    taskTable.classList.add("hidden");
    taskEmpty.classList.remove("hidden");
    statusLine.textContent = "Failed to load tracking data.";
    console.error(error);
  }
});

function renderTracking(payload) {
  sumRun.textContent = payload.run_id || "-";
  sumPatient.textContent = payload.patient_id || "-";
  sumRunStatus.textContent = payload.run_status || "-";
  sumTaskCount.textContent = String(payload.task_count || 0);
  sumEscalations.textContent = String(payload.escalation_count || 0);

  const tasks = Array.isArray(payload.tasks) ? payload.tasks : [];
  taskBody.innerHTML = "";

  if (!tasks.length) {
    taskTable.classList.add("hidden");
    taskEmpty.classList.remove("hidden");
    return;
  }

  for (const task of tasks) {
    const tr = document.createElement("tr");

    const titleCell = document.createElement("td");
    titleCell.textContent = task.task_title || "-";
    tr.appendChild(titleCell);

    const ownerCell = document.createElement("td");
    ownerCell.textContent = task.owner || "-";
    tr.appendChild(ownerCell);

    const statusCell = document.createElement("td");
    statusCell.textContent = task.status || "-";
    tr.appendChild(statusCell);

    const gapCell = document.createElement("td");
    gapCell.textContent = task.originating_gap_id || "-";
    tr.appendChild(gapCell);

    const dueCell = document.createElement("td");
    dueCell.textContent = task.due_at_utc || "-";
    tr.appendChild(dueCell);

    const escalationCell = document.createElement("td");
    const badge = document.createElement("span");
    badge.className = `badge ${task.escalated ? "badge-escalated" : "badge-normal"}`;
    badge.setAttribute("data-escalated", task.escalated ? "true" : "false");
    badge.textContent = task.escalated ? "Escalated" : "Normal";
    escalationCell.appendChild(badge);
    tr.appendChild(escalationCell);

    taskBody.appendChild(tr);
  }

  taskEmpty.classList.add("hidden");
  taskTable.classList.remove("hidden");
}
