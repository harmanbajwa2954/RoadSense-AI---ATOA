/*
  workspace.js
  --------------
  Drives the Analysis Workspace page:
    1. One shared upload (drag & drop or click-to-browse)
    2. Lazy per-tab analysis -- a tab's model only runs the first time that
       tab is opened for the current upload. Switching tabs after that just
       re-renders the cached result instantly.
*/

(function () {
  const uploadZone = document.getElementById("upload-zone");
  const fileInput = document.getElementById("file-input");
  const progressWrap = document.getElementById("upload-progress-wrap");
  const progressFill = document.getElementById("upload-progress-fill");
  const progressLabel = document.getElementById("upload-progress-label");
  const previewFrame = document.getElementById("preview-frame");
  const uploadMeta = document.getElementById("upload-meta");
  const metaFilename = document.getElementById("meta-filename");
  const metaType = document.getElementById("meta-type");
  const tabRow = document.getElementById("tab-row");
  const resultsArea = document.getElementById("results-area");

  if (!uploadZone) return; // not on this page

  const MODULE_ENDPOINTS = {
    lane: "/api/analyze/lane",
    traffic_sign: "/api/analyze/traffic-sign",
    pothole: "/api/analyze/pothole",
    emergency: "/api/analyze/emergency",
  };

  const MODULE_LABELS = {
    lane: "Lane Analysis",
    traffic_sign: "Traffic Sign Analysis",
    pothole: "Road Surface Inspection",
    emergency: "Emergency Vehicle Analysis",
  };

  let currentFilename = null;
  let currentMediaType = null;
  let activeTab = "lane";
  const resultCache = {}; // module -> result payload, reset on every new upload

  // --- Upload interactions -------------------------------------------------

  uploadZone.addEventListener("click", () => fileInput.click());

  ["dragenter", "dragover"].forEach((evt) =>
    uploadZone.addEventListener(evt, (e) => {
      e.preventDefault();
      uploadZone.classList.add("drag-active");
    })
  );
  ["dragleave", "drop"].forEach((evt) =>
    uploadZone.addEventListener(evt, (e) => {
      e.preventDefault();
      uploadZone.classList.remove("drag-active");
    })
  );
  uploadZone.addEventListener("drop", (e) => {
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files[0]) uploadFile(fileInput.files[0]);
  });

  function uploadFile(file) {
    const formData = new FormData();
    formData.append("file", file);

    progressWrap.style.display = "block";
    progressFill.style.width = "10%";
    progressLabel.textContent = `Uploading ${file.name}…`;

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/workspace/upload");

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        progressFill.style.width = pct + "%";
      }
    };

    xhr.onload = () => {
      let data;
      try {
        data = JSON.parse(xhr.responseText);
      } catch {
        data = { success: false, error: "Unexpected server response." };
      }

      if (!data.success) {
        progressWrap.style.display = "none";
        window.RoadSenseToast.show({
          type: "danger",
          title: "Upload failed",
          message: data.error || "Please try a different file.",
        });
        return;
      }

      progressFill.style.width = "100%";
      progressLabel.textContent = "Upload complete";

      currentFilename = data.filename;
      currentMediaType = data.media_type;
      Object.keys(resultCache).forEach((k) => delete resultCache[k]);

      renderPreview(data.preview_url, data.media_type);
      metaFilename.textContent = data.filename;
      metaType.textContent = data.media_type;
      uploadMeta.style.display = "flex";

      setTimeout(() => (progressWrap.style.display = "none"), 600);

      window.RoadSenseToast.show({
        type: "success",
        title: "Upload complete",
        message: "Select a tab to run that module's analysis.",
      });

      runActiveTab();
    };

    xhr.onerror = () => {
      progressWrap.style.display = "none";
      window.RoadSenseToast.show({ type: "danger", title: "Upload failed", message: "Network error." });
    };

    xhr.send(formData);
  }

  function renderPreview(url, mediaType) {
    previewFrame.style.display = "flex";
    if (mediaType === "video") {
      previewFrame.innerHTML = `<video src="${url}" controls></video>`;
    } else {
      previewFrame.innerHTML = `<img src="${url}" alt="Uploaded preview" />`;
    }
  }

  // --- Tab switching (lazy execution) --------------------------------------

  tabRow.addEventListener("click", (e) => {
    const btn = e.target.closest(".tab-btn");
    if (!btn) return;

    tabRow.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    activeTab = btn.dataset.tab;

    runActiveTab();
  });

  function runActiveTab() {
    if (!currentFilename) {
      renderEmpty("Upload media to begin", "Once uploaded, select a tab above to run that module's analysis.");
      return;
    }

    if (resultCache[activeTab]) {
      renderResult(resultCache[activeTab]);
      return;
    }

    renderLoading();

    fetch(MODULE_ENDPOINTS[activeTab], {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: currentFilename }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (!data.success) {
          renderError(data.result && data.result.error ? data.result.error : data.error || "Analysis failed.");
          window.RoadSenseToast.show({
            type: "danger",
            title: `${MODULE_LABELS[activeTab]} failed`,
            message: data.result && data.result.error ? data.result.error : "Check server logs.",
          });
          return;
        }
        resultCache[activeTab] = data.result;
        renderResult(data.result);
        window.RoadSenseToast.show({
          type: "info",
          title: "Processing complete",
          message: `${MODULE_LABELS[activeTab]} finished in ${data.result.inference_time}s.`,
        });
      })
      .catch(() => {
        renderError("Could not reach the analysis service.");
      });
  }

  function renderLoading() {
    resultsArea.innerHTML = `
      <div style="position:relative; min-height:280px;">
        <div class="loading-overlay">
          <div class="spinner-ring"></div>
          <div class="loading-text">RUNNING ${MODULE_LABELS[activeTab].toUpperCase()}…</div>
        </div>
      </div>
    `;
  }

  function renderEmpty(title, msg) {
    resultsArea.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/></svg></div>
        <h4>${title}</h4>
        <p>${msg}</p>
      </div>
    `;
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
    const detailRows = Object.entries(result.details || {})
      .map(
        ([k, v]) =>
          `<div class="meta-row"><span class="meta-label">${formatLabel(k)}</span><span class="meta-value">${v}</span></div>`
      )
      .join("");

    const mediaUrl = result.annotated_filename
      ? `/outputs/${result.module}/${result.annotated_filename}`
      : null;

    const mediaTag = mediaUrl
      ? result.media_type === "video"
        ? `<video src="${mediaUrl}" controls></video>`
        : `<img src="${mediaUrl}" alt="Annotated result" />`
      : `<span style="color:var(--text-muted); font-size: var(--fs-sm);">No annotated output produced.</span>`;

    resultsArea.innerHTML = `
      <div class="result-summary-strip">
        <div class="mini-stat"><div class="mini-label">Model</div><div class="mini-value" style="font-size: var(--fs-sm);">${result.model_name}</div></div>
        <div class="mini-stat"><div class="mini-label">Confidence</div><div class="mini-value">${result.confidence ?? "—"}%</div></div>
        <div class="mini-stat"><div class="mini-label">Objects Detected</div><div class="mini-value">${result.objects_detected ?? "—"}</div></div>
        <div class="mini-stat"><div class="mini-label">Inference Time</div><div class="mini-value">${result.inference_time ?? "—"}s</div></div>
      </div>
      <div class="result-grid">
        <div>
          <span class="card-label">Annotated Output</span>
          <div class="media-frame" style="margin-top: var(--sp-3);">${mediaTag}</div>
          ${
            mediaUrl
              ? `<a class="btn btn-secondary btn-sm" style="margin-top: var(--sp-4);" href="${mediaUrl}" download>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                  Download Result
                 </a>`
              : ""
          }
        </div>
        <div>
          <span class="card-label">Analysis Summary</span>
          <div class="result-meta-list" style="margin-top: var(--sp-3);">
            <div class="meta-row"><span class="meta-label">Processing Status</span><span class="badge green">${result.status}</span></div>
            ${detailRows}
          </div>
        </div>
      </div>
    `;
  }

  function formatLabel(key) {
    return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }
})();
