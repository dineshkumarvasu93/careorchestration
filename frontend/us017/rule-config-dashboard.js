const apiBase = "http://localhost:8000";

const publishForm = document.getElementById("publish-form");
const publishStatus = document.getElementById("publish-status");

const activateForm = document.getElementById("activate-form");
const activateStatus = document.getElementById("activate-status");
const activeVersionLabel = document.getElementById("active-version");

const refreshButton = document.getElementById("refresh-button");
const versionList = document.getElementById("version-list");

const thresholdInput = document.getElementById("threshold");
const thresholdValue = document.getElementById("threshold-value");

// Fixed confidence weights for the prototype rule engine.
const CONFIDENCES = {
  uacr_missing_confidence: 0.92,
  egfr_decline_confidence: 0.88,
  high_risk_plan_confidence: 0.9,
};

// The known_gap_ids / include_high_risk_plan values come from the Flutter
// drag-and-drop island (an <iframe>) via postMessage. We seed with the default
// full ruleset so Publish still works before the island reports, or if the
// embedded component fails to load.
let latestRuleset = {
  known_gap_ids: [
    "GAP-UACR-MISSING",
    "GAP-EGFR-DECLINE",
    "GAP-CKD-HIGH-RISK-PLAN",
    "GAP-NO-ACTION",
  ],
  include_high_risk_plan: true,
};

window.addEventListener("message", (event) => {
  const data = event.data;
  if (!data || data.type !== "ruleset") {
    return;
  }
  latestRuleset = {
    known_gap_ids: Array.isArray(data.known_gap_ids)
      ? data.known_gap_ids.map(String)
      : [],
    include_high_risk_plan: Boolean(data.include_high_risk_plan),
  };
});

/* ------------------------------- Slider ---------------------------------- */

thresholdInput.addEventListener("input", () => {
  thresholdValue.textContent = thresholdInput.value;
});

/* -------------------------------- Publish -------------------------------- */

publishForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const payload = {
    version: String(document.getElementById("version").value || "").trim(),
    description: String(document.getElementById("description").value || "").trim(),
    egfr_decline_threshold: Number(thresholdInput.value || "0"),
    ...CONFIDENCES,
    include_high_risk_plan: latestRuleset.include_high_risk_plan,
    known_gap_ids: latestRuleset.known_gap_ids,
  };

  publishStatus.textContent = `Publishing ${payload.version}...`;

  try {
    const response = await fetch(`${apiBase}/api/v1/orchestration/rules/publish`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "publish failed");
    }

    publishStatus.textContent = `Published ${payload.version}.`;
    await loadVersions();
  } catch (error) {
    publishStatus.textContent = `Publish blocked: ${error.message}`;
  }
});

/* ------------------------------- Activate -------------------------------- */

activateForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const version = String(document.getElementById("activate-version").value || "").trim();
  if (!version) {
    activateStatus.textContent = "Version is required.";
    return;
  }

  activateStatus.textContent = `Activating ${version}...`;

  try {
    const response = await fetch(`${apiBase}/api/v1/orchestration/rules/activate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ version, actor: "ui-coordinator" }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || "activation failed");
    }

    const payload = await response.json();
    activeVersionLabel.textContent = payload.active_version || "-";
    activateStatus.textContent = `Activated ${version}.`;
    await loadVersions();
  } catch (error) {
    activateStatus.textContent = `Activation failed: ${error.message}`;
  }
});

refreshButton.addEventListener("click", async () => {
  await loadVersions();
});

async function loadVersions() {
  try {
    const response = await fetch(`${apiBase}/api/v1/orchestration/rules/versions`);
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }

    const payload = await response.json();
    activeVersionLabel.textContent = payload.active_version || "-";
    renderVersionList(Array.isArray(payload.versions) ? payload.versions : []);
  } catch (error) {
    renderVersionList([]);
    activateStatus.textContent = "Failed to load versions.";
  }
}

function renderVersionList(versions) {
  versionList.innerHTML = "";
  for (const version of versions) {
    const li = document.createElement("li");
    const versionText = String(version.version || "unknown");
    const descriptionText = String(version.description || "");
    const thresholdText = String(version.egfr_decline_threshold || "-");
    li.textContent = `${versionText} - ${descriptionText} (threshold ${thresholdText})`;
    versionList.appendChild(li);
  }
}

loadVersions();
