/*
  live_detection.js
  --------------------
  Live Detection Lab: each .live-card runs entirely independently of the
  others. Starting one card's webcam feed has no effect on any other card,
  matching the "no unified live pipeline" requirement.
*/

(function () {
  const cards = document.querySelectorAll(".live-card");
  if (!cards.length) return;

  cards.forEach((card) => {
    const moduleKey = card.dataset.module;
    const video = card.querySelector(".live-video");
    const resultImg = card.querySelector(".live-result");
    const canvas = card.querySelector(".live-canvas");
    const placeholder = card.querySelector(".feed-placeholder");
    const startBtn = card.querySelector(".start-btn");
    const stopBtn = card.querySelector(".stop-btn");
    const statusBadge = card.querySelector(".status-badge");
    const resultEl = card.querySelector(".live-card-result");
    const feedFrame = card.querySelector(".feed-frame");

    let stream = null;
    let isActive = false;

    async function processFrame() {
      if (!isActive) return;

      if (video.videoWidth > 0 && video.videoHeight > 0) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext("2d");
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        const base64Img = canvas.toDataURL("image/jpeg", 0.7);

        try {
          const res = await fetch(`/api/live/analyze-frame/${moduleKey}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ image: base64Img }),
          });
          
          if (res.ok) {
            const data = await res.json();
            if (data.success) {
              resultImg.src = data.image;
              resultImg.style.display = "block";
              
              const metricsStr = Object.entries(data.metrics || {})
                .map(([k, v]) => `${k.replace("_", " ")}: ${v}`)
                .join(" · ");
              resultEl.textContent = metricsStr || "Running...";
            }
          }
        } catch (e) {
          console.error("Frame analysis error:", e);
        }
      }
      
      // Queue next frame
      setTimeout(() => {
        if (isActive) requestAnimationFrame(processFrame);
      }, 150); // Polling delay to save CPU
    }

    startBtn.addEventListener("click", async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: true });
      } catch (err) {
        window.RoadSenseToast.show({
          type: "danger",
          title: "Camera unavailable",
          message: `Could not access a webcam for ${moduleKey.replace("_", " ")}.`,
        });
        return;
      }

      video.srcObject = stream;
      video.style.display = "block";
      placeholder.style.display = "none";

      const recIndicator = document.createElement("div");
      recIndicator.className = "rec-indicator";
      recIndicator.innerHTML = `<span class="rec-dot"></span> LIVE`;
      feedFrame.appendChild(recIndicator);

      statusBadge.textContent = "Running";
      statusBadge.className = "badge green status-badge";
      startBtn.disabled = true;
      stopBtn.disabled = false;
      resultEl.textContent = "Initializing model…";

      isActive = true;
      video.play().then(() => {
        processFrame();
      }).catch((e) => {
        console.error("Video play failed:", e);
        processFrame();
      });
    });

    stopBtn.addEventListener("click", () => {
      isActive = false;
      if (stream) {
        stream.getTracks().forEach((t) => t.stop());
        stream = null;
      }

      video.style.display = "none";
      resultImg.style.display = "none";
      placeholder.style.display = "flex";
      
      const rec = feedFrame.querySelector(".rec-indicator");
      if (rec) rec.remove();

      statusBadge.textContent = "Idle";
      statusBadge.className = "badge gray status-badge";
      startBtn.disabled = false;
      stopBtn.disabled = true;
      resultEl.textContent = "Awaiting start…";
    });
  });
})();
