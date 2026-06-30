/*
  drowsiness.js
  ---------------
  Driver Monitoring page: dedicated upload that runs only the drowsiness
  model and renders Driver Status / Eye Status / Yawning Status / Fatigue
  Level / Inference Time / Result Video.
*/

(function () {
  const zone = document.getElementById("dr-upload-zone");
  const fileInput = document.getElementById("dr-file-input");
  const progressWrap = document.getElementById("dr-progress-wrap");
  const progressFill = document.getElementById("dr-progress-fill");
  const progressLabel = document.getElementById("dr-progress-label");
  const resultsArea = document.getElementById("dr-results-area");
  const companionBtn = document.getElementById("companion-download-btn");

  if (!zone) return;

  zone.addEventListener("click", () => fileInput.click());

  ["dragenter", "dragover"].forEach((evt) =>
    zone.addEventListener(evt, (e) => {
      e.preventDefault();
      zone.classList.add("drag-active");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    zone.addEventListener(evt, (e) => {
      e.preventDefault();
      zone.classList.remove("drag-active");
    })
  );
  zone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files[0];
    if (file) uploadAndAnalyze(file);
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) uploadAndAnalyze(fileInput.files[0]);
  });

  companionBtn.addEventListener("click", () => {
    window.RoadSenseToast.show({
      type: "info",
      title: "Companion app",
      message: "Pairing is only available on the physical demo rig during the viva.",
    });
  });

  function uploadAndAnalyze(file) {
    const formData = new FormData();
    formData.append("file", file);

    progressWrap.style.display = "block";
    progressFill.style.width = "10%";
    progressLabel.textContent = `Uploading ${file.name}…`;

    resultsArea.innerHTML = `
      <div style="position:relative; min-height:200px;">
        <div class="loading-overlay">
          <div class="spinner-ring"></div>
          <div class="loading-text">RUNNING DROWSINESS DETECTION…</div>
        </div>
      </div>
    `;

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/drowsiness/upload-and-analyze");

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 90); // cap at 90 until inference returns
        progressFill.style.width = pct + "%";
      }
    };

    xhr.onload = () => {
      progressFill.style.width = "100%";
      progressLabel.textContent = "Done";
      setTimeout(() => (progressWrap.style.display = "none"), 500);

      let data;
      try {
        data = JSON.parse(xhr.responseText);
      } catch {
        data = { success: false, error: "Unexpected server response." };
      }

      if (!data.success) {
        renderError(data.result && data.result.error ? data.result.error : data.error || "Analysis failed.");
        window.RoadSenseToast.show({
          type: "danger",
          title: "Driver monitoring failed",
          message: data.result && data.result.error ? data.result.error : "Check server logs.",
        });
        return;
      }

      renderResult(data.result);

      const fatigueIsHigh = (data.result.details.fatigue_level || "").toLowerCase() === "high";
      window.RoadSenseToast.show({
        type: fatigueIsHigh ? "warning" : "success",
        title: fatigueIsHigh ? "Fatigue Level High" : "Processing Complete",
        message: `Driver status: ${data.result.details.driver_status}`,
      });
    };

    xhr.onerror = () => {
      progressWrap.style.display = "none";
      window.RoadSenseToast.show({ type: "danger", title: "Upload failed", message: "Network error." });
    };

    xhr.send(formData);
  }

  function renderError(message) {
    resultsArea.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon" style="color: var(--alert-red);"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></div>
        <h4>Analysis failed</h4>
        <p>${message}</p>
      </div>
    `;
  }

  function renderResult(result) {
    const d = result.details || {};
    const mediaUrl = result.annotated_filename ? `/outputs/drowsiness/${result.annotated_filename}` : null;
    const statusBadgeClass = (d.driver_status || "").toLowerCase() === "alert" ? "green" : "amber";

    resultsArea.innerHTML = `
      <div class="media-frame" style="margin-bottom: var(--sp-5);">
        ${mediaUrl ? `<video src="${mediaUrl}" controls></video>` : `<span style="color:var(--text-muted); font-size: var(--fs-sm);">No result video produced.</span>`}
      </div>
      <div class="driver-status-cards">
        <div class="mini-stat"><div class="mini-label">Driver Status</div><div class="mini-value"><span class="badge ${statusBadgeClass}">${d.driver_status || "—"}</span></div></div>
        <div class="mini-stat"><div class="mini-label">Eye Status</div><div class="mini-value" style="font-size: var(--fs-sm);">${d.eye_status || "—"}</div></div>
        <div class="mini-stat"><div class="mini-label">Yawning Status</div><div class="mini-value" style="font-size: var(--fs-sm);">${d.yawning_status || "—"}</div></div>
        <div class="mini-stat"><div class="mini-label">Fatigue Level</div><div class="mini-value" style="font-size: var(--fs-sm);">${d.fatigue_level || "—"}</div></div>
      </div>
      <div class="result-meta-list" style="margin-top: var(--sp-5);">
        <div class="meta-row"><span class="meta-label">Inference Time</span><span class="meta-value">${result.inference_time ?? "—"}s</span></div>
        <div class="meta-row"><span class="meta-label">Confidence</span><span class="meta-value">${result.confidence ?? "—"}%</span></div>
      </div>
      ${
        mediaUrl
          ? `<a class="btn btn-secondary btn-sm" style="margin-top: var(--sp-5);" href="${mediaUrl}" download>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              Download Result
             </a>`
          : ""
      }
    `;
  }
})();
