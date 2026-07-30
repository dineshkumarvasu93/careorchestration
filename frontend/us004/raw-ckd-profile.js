const apiBase = window.location.origin.startsWith("http")
  ? "http://localhost:8000"
  : "http://localhost:8000";

const searchForm = document.getElementById("search-form");
const searchInput = document.getElementById("patient-query");
const searchStatus = document.getElementById("search-status");
const searchResults = document.getElementById("search-results");
const profileEmpty = document.getElementById("profile-empty");
const profileFields = document.getElementById("profile-fields");

const fieldPatientId = document.getElementById("field-patient-id");
const fieldName = document.getElementById("field-name");
const fieldCkdStage = document.getElementById("field-ckd-stage");
const fieldEgfrCurrent = document.getElementById("field-egfr-current");
const fieldEgfrPrevious = document.getElementById("field-egfr-previous");
const fieldUacrStatus = document.getElementById("field-uacr-status");
const fieldLastVisit = document.getElementById("field-last-visit");

searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = searchInput.value.trim();
  if (!query) {
    searchStatus.textContent = "Enter a patient query.";
    return;
  }

  searchStatus.textContent = "Searching...";
  searchResults.innerHTML = "";

  try {
    const response = await fetch(`${apiBase}/api/v1/patients?query=${encodeURIComponent(query)}`);
    const payload = await response.json();
    const results = Array.isArray(payload.results) ? payload.results : [];

    if (!results.length) {
      searchStatus.textContent = "No matches found.";
      return;
    }

    searchStatus.textContent = `${results.length} patient(s) found.`;
    for (const item of results) {
      const li = document.createElement("li");
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = `${item.name} (${item.patient_id}) - ${item.ckd_stage}`;
      button.addEventListener("click", () => loadProfile(item.patient_id));
      li.appendChild(button);
      searchResults.appendChild(li);
    }
  } catch (error) {
    searchStatus.textContent = "Search failed. Ensure backend is running.";
    console.error(error);
  }
});

async function loadProfile(patientId) {
  searchStatus.textContent = `Loading profile ${patientId}...`;
  try {
    const response = await fetch(`${apiBase}/api/v1/patients/${encodeURIComponent(patientId)}/profile`);
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }

    const payload = await response.json();
    renderProfile(payload.profile);
    searchStatus.textContent = `Loaded profile for ${payload.profile.patient_id}.`;
  } catch (error) {
    searchStatus.textContent = "Profile load failed.";
    console.error(error);
  }
}

function renderProfile(profile) {
  profileEmpty.classList.add("hidden");
  profileFields.classList.remove("hidden");

  fieldPatientId.textContent = profile.patient_id || "-";
  fieldName.textContent = `${profile.demographics.first_name} ${profile.demographics.last_name}`;
  fieldCkdStage.textContent = profile.ckd_stage || "-";
  fieldEgfrCurrent.textContent = `${profile.egfr.current ?? "-"}`;
  fieldEgfrPrevious.textContent = `${profile.egfr.previous ?? "-"}`;
  fieldUacrStatus.textContent = profile.uacr.status || "-";
  fieldLastVisit.textContent = profile.last_nephrology_visit_date || "-";
}
