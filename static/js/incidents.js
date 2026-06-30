/*
  incidents.js
  --------------
  Incident Monitoring page: severity filter chips + create/edit/delete
  modal wired to the /api/incidents CRUD endpoints.
*/

(function () {
  const tbody = document.getElementById("incident-tbody");
  const filterRow = document.getElementById("filter-row");
  const newBtn = document.getElementById("new-incident-btn");
  const modalBackdrop = document.getElementById("incident-modal-backdrop");
  const modalClose = document.getElementById("incident-modal-close");
  const cancelBtn = document.getElementById("incident-cancel-btn");
  const form = document.getElementById("incident-form");
  const modalTitle = document.getElementById("incident-modal-title");

  if (!tbody) return;

  const idField = document.getElementById("incident-id");
  const locationField = document.getElementById("incident-location");
  const severityField = document.getElementById("incident-severity");
  const statusField = document.getElementById("incident-status");
  const vehicleField = document.getElementById("incident-vehicle");
  const notesField = document.getElementById("incident-notes");

  // --- Severity filter chips -----------------------------------------------

  filterRow.addEventListener("click", (e) => {
    const chip = e.target.closest(".chip-filter");
    if (!chip) return;
    filterRow.querySelectorAll(".chip-filter").forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");

    const value = chip.dataset.value;
    tbody.querySelectorAll("tr[data-severity]").forEach((row) => {
      row.style.display = value === "all" || row.dataset.severity === value ? "" : "none";
    });
  });

  // --- Modal open/close -----------------------------------------------------

  function openModal(mode, data) {
    modalTitle.textContent = mode === "edit" ? `Edit Incident ${data.incident_code}` : "Log Incident";
    idField.value = data.id || "";
    locationField.value = data.location || "";
    severityField.value = data.severity || "Minor";
    statusField.value = data.status || "Active";
    vehicleField.value = data.vehicle_type || "";
    notesField.value = data.notes || "";
    modalBackdrop.classList.add("open");
  }

  function closeModal() {
    modalBackdrop.classList.remove("open");
  }

  newBtn.addEventListener("click", () => openModal("create", {}));
  modalClose.addEventListener("click", closeModal);
  cancelBtn.addEventListener("click", closeModal);
  modalBackdrop.addEventListener("click", (e) => {
    if (e.target === modalBackdrop) closeModal();
  });

  // --- Row actions: edit / delete --------------------------------------------

  tbody.addEventListener("click", (e) => {
    const editBtn = e.target.closest(".edit-incident-btn");
    const deleteBtn = e.target.closest(".delete-incident-btn");

    if (editBtn) {
      const id = editBtn.dataset.id;
      fetch(`/api/incidents/${id}`)
        .then((r) => r.json())
        .then((data) => {
          if (data.success) openModal("edit", data.incident);
        });
    }

    if (deleteBtn) {
      const id = deleteBtn.dataset.id;
      const row = deleteBtn.closest("tr");
      if (!confirm("Delete this incident record? This cannot be undone.")) return;

      fetch(`/api/incidents/${id}`, { method: "DELETE" })
        .then((r) => r.json())
        .then((data) => {
          if (data.success) {
            row.remove();
            window.RoadSenseToast.show({ type: "success", title: "Incident deleted" });
          }
        });
    }
  });

  // --- Form submit (create or update) ----------------------------------------

  form.addEventListener("submit", (e) => {
    e.preventDefault();

    const payload = {
      location: locationField.value,
      severity: severityField.value,
      status: statusField.value,
      vehicle_type: vehicleField.value,
      notes: notesField.value,
    };

    const id = idField.value;
    const url = id ? `/api/incidents/${id}` : "/api/incidents";
    const method = id ? "PUT" : "POST";

    fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then((r) => r.json())
      .then((data) => {
        if (!data.success) {
          window.RoadSenseToast.show({ type: "danger", title: "Save failed", message: data.error || "" });
          return;
        }
        closeModal();
        window.RoadSenseToast.show({
          type: "success",
          title: id ? "Incident updated" : "Incident logged",
          message: data.incident.incident_code,
        });
        location.reload();
      });
  });
})();
