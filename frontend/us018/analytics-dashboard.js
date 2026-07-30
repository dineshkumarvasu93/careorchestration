const apiBase = "http://localhost:8000";

const refreshButton = document.getElementById("refresh-button");
const statusLine = document.getElementById("status-line");
const widgetGrid = document.getElementById("widget-grid");

const totalRuns = document.getElementById("total-runs");
const decidedRuns = document.getElementById("decided-runs");
const approvedRuns = document.getElementById("approved-runs");
const rejectedRuns = document.getElementById("rejected-runs");
const tasksGeneratedRuns = document.getElementById("tasks-generated-runs");
const avgTaskGenerationLatency = document.getElementById("avg-task-generation-latency");

refreshButton.addEventListener("click", async () => {
  statusLine.textContent = "Loading analytics...";

  try {
    const response = await fetch(`${apiBase}/api/v1/orchestration/analytics`);
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }

    const payload = await response.json();
    renderWidgets(Array.isArray(payload.widgets) ? payload.widgets : []);
    renderDetails(payload);
    statusLine.textContent = "Analytics loaded.";
  } catch (error) {
    statusLine.textContent = "Unable to load analytics.";
    console.error(error);
  }
});

function renderWidgets(widgets) {
  widgetGrid.innerHTML = "";

  for (const widget of widgets) {
    const card = document.createElement("article");
    card.className = "widget";

    const label = document.createElement("span");
    label.className = "widget-label";
    label.textContent = widget.label || "Metric";

    const value = document.createElement("span");
    value.className = "widget-value";
    value.textContent = widget.value || "0";

    card.appendChild(label);
    card.appendChild(value);
    widgetGrid.appendChild(card);
  }
}

function renderDetails(payload) {
  const approval = payload.approval || {};
  const conversion = payload.conversion || {};
  const latency = payload.latency || {};

  totalRuns.textContent = String(approval.total_runs || 0);
  decidedRuns.textContent = String(approval.decided_runs || 0);
  approvedRuns.textContent = String(approval.approved_runs || 0);
  rejectedRuns.textContent = String(approval.rejected_runs || 0);
  tasksGeneratedRuns.textContent = String(conversion.tasks_generated_runs || 0);
  avgTaskGenerationLatency.textContent = String(latency.average_task_generation_latency_seconds || 0);
}
