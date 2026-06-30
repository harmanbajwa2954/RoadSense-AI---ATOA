/*
  crash_alert.js
  ----------------
  ATOA Crash Detection & Proximity Alert System.

  Client-side logic ported from the standalone ATOA prototype:
    1. State machine: IDLE → ACTIVE → CRASHED / ALERTING
    2. Device sensors: GPS (speed + coords) + accelerometer (G-force)
    3. Crash model: G-force threshold + speed check on 3-second interval
    4. Firebase broadcasting: push/listen on live_alerts node
    5. Speech synthesis: verbal warnings for nearby crash alerts
    6. Server logging: POST crash data to /api/crash-alert/log
*/

(function () {
  "use strict";

  // ── Firebase Configuration ──
  const FIREBASE_CONFIG = {
    apiKey: "AIzaSyBlN3sL3gu3M0btRZJjVS_saV0sqEx1c4c",
    authDomain: "atoa-alert-system.firebaseapp.com",
    databaseURL: "https://atoa-alert-system-default-rtdb.firebaseio.com",
    projectId: "atoa-alert-system",
    storageBucket: "atoa-alert-system.firebasestorage.app",
    messagingSenderId: "213165942729",
    appId: "1:213165942729:web:ff209c5b20b61f76b1aa18",
  };

  // ── Model thresholds ──
  const G_FORCE_THRESHOLD = 6.0;
  const SPEED_THRESHOLD = 5; // km/h — car must be stopped
  const ALERT_RADIUS_KM = 2;
  const CHECK_INTERVAL_MS = 3000;

  // ── State ──
  const DEVICE_ID = "device_" + Math.random().toString(36).substr(2, 9);
  let systemState = "IDLE"; // IDLE, ACTIVE, CRASHED, ALERTING
  let currentSpeed = 0;
  let currentLocation = { lat: 0, lon: 0 };
  let maxGForce = 0;
  let nearbyAlertCount = 0;
  let checkInterval = null;
  let watchId = null;

  // ── Firebase refs ──
  let database = null;
  let alertsRef = null;

  // ── DOM elements ──
  const activateBtn = document.getElementById("atoa-activate-btn");
  const activateWrap = document.getElementById("atoa-activate-wrap");
  const telemetry = document.getElementById("atoa-telemetry");
  const deactivateBtn = document.getElementById("atoa-deactivate-btn");
  const alertBanner = document.getElementById("atoa-alert-banner");
  const dismissBannerBtn = document.getElementById("atoa-dismiss-banner-btn");
  const alertFeed = document.getElementById("atoa-alert-feed");
  const emptyFeed = document.getElementById("atoa-empty-feed");

  // Stat cards
  const speedStatEl = document.getElementById("atoa-speed");
  const gforceStatEl = document.getElementById("atoa-gforce");
  const systemStateEl = document.getElementById("atoa-system-state");
  const alertCountEl = document.getElementById("atoa-alert-count");
  const gforceIcon = document.getElementById("atoa-gforce-icon");
  const alertCountIcon = document.getElementById("atoa-alert-count-icon");

  // Telemetry readouts
  const teleSpeed = document.getElementById("atoa-tele-speed");
  const teleGforce = document.getElementById("atoa-tele-gforce");
  const speedFill = document.getElementById("atoa-speed-fill");
  const gforceFill = document.getElementById("atoa-gforce-fill");
  const gpsCoords = document.getElementById("atoa-gps-coords");

  // State badge
  const stateBadge = document.getElementById("atoa-state-badge");
  const stateText = document.getElementById("atoa-state-text");

  // Connection status
  const firebaseStatus = document.getElementById("atoa-firebase-status");
  const gpsAccuracy = document.getElementById("atoa-gps-accuracy");
  const sensorStatus = document.getElementById("atoa-sensor-status");
  const speechStatus = document.getElementById("atoa-speech-status");
  const feedStatus = document.getElementById("atoa-feed-status");

  // Banner text
  const bannerTitle = document.getElementById("atoa-alert-banner-title");
  const bannerSub = document.getElementById("atoa-alert-banner-sub");

  if (!activateBtn) return; // Not on the crash-alert page

  // ── Initialize Firebase ──
  function initFirebase() {
    try {
      if (!firebase.apps.length) {
        firebase.initializeApp(FIREBASE_CONFIG);
      }
      database = firebase.database();
      alertsRef = database.ref("live_alerts");
      firebaseStatus.textContent = "Connected ✓";
      firebaseStatus.style.color = "var(--signal-green)";
    } catch (err) {
      console.error("Firebase init failed:", err);
      firebaseStatus.textContent = "Connection failed";
      firebaseStatus.style.color = "var(--alert-red)";
    }
  }

  // ── State management ──
  function setState(newState) {
    systemState = newState;
    systemStateEl.textContent = newState;
    stateText.textContent = newState;

    // Update badge color
    stateBadge.className = "badge";
    switch (newState) {
      case "IDLE":
        stateBadge.classList.add("gray");
        systemStateEl.style.color = "var(--text-muted)";
        break;
      case "ACTIVE":
        stateBadge.classList.add("green");
        systemStateEl.style.color = "var(--signal-green)";
        break;
      case "CRASHED":
        stateBadge.classList.add("red");
        systemStateEl.style.color = "var(--alert-red)";
        break;
      case "ALERTING":
        stateBadge.classList.add("amber");
        systemStateEl.style.color = "var(--alert-amber)";
        break;
    }
  }

  // ── Activation ──
  activateBtn.addEventListener("click", () => {
    // Unlock browser audio with a test speak
    speak("System activated.");

    activateWrap.style.display = "none";
    telemetry.style.display = "block";
    setState("ACTIVE");
    sensorStatus.textContent = "Active ✓";
    sensorStatus.style.color = "var(--signal-green)";

    startSensorMonitoring();
    startCrashModel();
    startAlertListener();

    if (window.RoadSenseToast) {
      window.RoadSenseToast.show({
        type: "success",
        title: "ATOA System Activated",
        message: "Crash detection sensors are now monitoring.",
      });
    }
  });

  // ── Deactivation ──
  deactivateBtn.addEventListener("click", () => {
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    
    if (watchId !== null) {
      navigator.geolocation.clearWatch(watchId);
      watchId = null;
    }
    if (checkInterval !== null) {
      clearInterval(checkInterval);
      checkInterval = null;
    }
    if (alertsRef) {
      alertsRef.off("child_added");
    }

    activateWrap.style.display = "block";
    telemetry.style.display = "none";
    alertBanner.style.display = "none";
    setState("IDLE");
    sensorStatus.textContent = "Idle";
    sensorStatus.style.color = "";
    maxGForce = 0;
    currentSpeed = 0;

    updateSpeedDisplay(0);
    updateGForceDisplay(0);

    if (window.RoadSenseToast) {
      window.RoadSenseToast.show({
        type: "info",
        title: "ATOA System Deactivated",
      });
    }
  });

  // ── Dismiss banner ──
  dismissBannerBtn.addEventListener("click", () => {
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    
    alertBanner.style.display = "none";
    alertBanner.classList.remove("crash", "warning");
    if (systemState === "ALERTING" || systemState === "CRASHED") {
      setState("ACTIVE");
    }
  });

  // ── Dismiss feed item buttons ──
  alertFeed.addEventListener("click", (e) => {
    const btn = e.target.closest(".atoa-dismiss-btn");
    if (!btn) return;

    if (window.speechSynthesis) window.speechSynthesis.cancel();

    const id = btn.dataset.id;
    fetch(`/api/crash-alert/dismiss/${id}`, { method: "POST" })
      .then((r) => r.json())
      .then((data) => {
        if (data.success) {
          const item = btn.closest(".atoa-feed-item");
          if (item) item.remove();
          nearbyAlertCount = Math.max(0, nearbyAlertCount - 1);
          alertCountEl.textContent = nearbyAlertCount;
        }
      });
  });

  // ── Sensor Monitoring ──
  function startSensorMonitoring() {
    // GPS
    if (navigator.geolocation) {
      watchId = navigator.geolocation.watchPosition(
        (position) => {
          currentSpeed = position.coords.speed
            ? position.coords.speed * 3.6
            : 0;
          currentLocation.lat = position.coords.latitude;
          currentLocation.lon = position.coords.longitude;

          updateSpeedDisplay(currentSpeed);
          gpsCoords.textContent = `${currentLocation.lat.toFixed(5)}, ${currentLocation.lon.toFixed(5)}`;
          gpsAccuracy.textContent = `±${Math.round(position.coords.accuracy || 0)}m`;

          if (systemState === "ACTIVE") {
            speedStatEl.innerHTML = `${currentSpeed.toFixed(1)} <small style="font-size:0.5em; color:var(--text-muted);">km/h</small>`;
          }
        },
        (err) => {
          gpsCoords.textContent = "GPS Error: " + err.message;
          gpsAccuracy.textContent = "Unavailable";
        },
        { enableHighAccuracy: true }
      );
    } else {
      gpsCoords.textContent = "GPS not supported";
    }

    // Accelerometer
    if (window.DeviceMotionEvent) {
      window.addEventListener("devicemotion", (event) => {
        const a = event.acceleration || event.accelerationIncludingGravity;
        if (!a) return;

        const gforce =
          Math.sqrt(
            (a.x || 0) ** 2 + (a.y || 0) ** 2 + (a.z || 0) ** 2
          ) / 9.81;

        if (gforce > maxGForce) {
          maxGForce = gforce;
          updateGForceDisplay(maxGForce);

          if (systemState === "ACTIVE" || systemState === "CRASHED") {
            gforceStatEl.innerHTML = `${maxGForce.toFixed(1)} <small style="font-size:0.5em; color:var(--text-muted);">Gs</small>`;
          }
        }
      });
    }

    // Check speech synthesis support
    if ("speechSynthesis" in window) {
      speechStatus.textContent = "Available ✓";
      speechStatus.style.color = "var(--signal-green)";
    } else {
      speechStatus.textContent = "Not supported";
      speechStatus.style.color = "var(--alert-amber)";
    }
  }

  // ── UI update helpers ──
  function updateSpeedDisplay(speed) {
    if (teleSpeed) {
      teleSpeed.querySelector(".atoa-tele-num").textContent = speed.toFixed(1);
    }
    if (speedFill) {
      speedFill.style.width = Math.min(100, (speed / 120) * 100) + "%";
    }
  }

  function updateGForceDisplay(gforce) {
    if (teleGforce) {
      teleGforce.querySelector(".atoa-tele-num").textContent = gforce.toFixed(1);
    }
    if (gforceFill) {
      const pct = Math.min(100, (gforce / 10) * 100);
      gforceFill.style.width = pct + "%";

      // Color-code based on severity
      if (gforce > G_FORCE_THRESHOLD) {
        gforceFill.style.background = "var(--alert-red)";
      } else if (gforce > G_FORCE_THRESHOLD * 0.6) {
        gforceFill.style.background = "var(--alert-amber)";
      } else {
        gforceFill.style.background = "";
      }
    }

    // Update stat card icon color
    if (gforceIcon) {
      gforceIcon.className = gforce > G_FORCE_THRESHOLD ? "stat-icon red" :
                              gforce > G_FORCE_THRESHOLD * 0.6 ? "stat-icon amber" : "stat-icon green";
    }
  }

  // ── Crash Detection Model ──
  function startCrashModel() {
    checkInterval = setInterval(() => {
      if (
        systemState === "ACTIVE" &&
        maxGForce > G_FORCE_THRESHOLD &&
        currentSpeed < SPEED_THRESHOLD
      ) {
        console.log(
          `CRASH DETECTED! G-Force: ${maxGForce.toFixed(1)}, Speed: ${currentSpeed.toFixed(1)}`
        );
        setState("CRASHED");
        showAlertBanner(
          "💥 CRASH DETECTED",
          "Sending alert to nearby drivers...",
          "crash"
        );
        sendAlert();
        logCrashToServer();
      }

      // Reset max G-force for next window
      maxGForce = 0;
      if (systemState === "ACTIVE") {
        updateGForceDisplay(0);
        gforceStatEl.innerHTML = `0.0 <small style="font-size:0.5em; color:var(--text-muted);">Gs</small>`;
      }
    }, CHECK_INTERVAL_MS);
  }

  // ── Alert Banner ──
  function showAlertBanner(title, subtitle, type) {
    bannerTitle.textContent = title;
    bannerSub.textContent = subtitle;
    alertBanner.className = "atoa-alert-banner " + (type || "");
    alertBanner.style.display = "flex";
  }

  // ── Firebase: Send Alert ──
  function sendAlert() {
    if (!alertsRef) return;

    const alertId = "alert_" + Date.now();
    alertsRef.child(alertId).set({
      deviceId: DEVICE_ID,
      lat: currentLocation.lat,
      lon: currentLocation.lon,
      time: Date.now(),
    });

    // Auto-remove from Firebase after 1 hour
    setTimeout(() => {
      alertsRef.child(alertId).remove();
    }, 3600 * 1000);
  }

  // ── Firebase: Listen for Alerts ──
  function startAlertListener() {
    if (!alertsRef) return;

    feedStatus.textContent = "Live";
    feedStatus.className = "badge green";

    // Remove any existing listener first to prevent duplicates
    alertsRef.off("child_added");

    // Only listen for alerts from the last 5 minutes
    const fiveMinutesAgo = Date.now() - 5 * 60 * 1000;
    
    alertsRef.orderByChild("time").startAt(fiveMinutesAgo).on("child_added", (snapshot) => {
      const alertData = snapshot.val();
      
      // Ignore alerts sent by this exact device
      if (alertData.deviceId === DEVICE_ID) return;
      
      // Ignore if we are the one crashing
      if (systemState === "CRASHED") return;

      const dist = getDistance(
        currentLocation.lat,
        currentLocation.lon,
        alertData.lat,
        alertData.lon
      );

      console.log(`New alert received, ${dist.toFixed(2)} km away.`);

      if (dist < ALERT_RADIUS_KM) {
        setState("ALERTING");
        
        let distText = dist.toFixed(1) + " kilometers";
        if (dist < 0.1) {
          distText = "less than 100 meters";
        }
        
        speak(
          `Caution: Accident reported ${distText} ahead! Slow down!`
        );
        showAlertBanner(
          "⚠️ ACCIDENT NEARBY",
          `Crash reported ${distText} away — slow down!`,
          "warning"
        );

        nearbyAlertCount++;
        alertCountEl.textContent = nearbyAlertCount;
        alertCountIcon.className = "stat-icon red";

        // Add to feed
        addFeedItem(alertData, dist, snapshot.key);
      }
    });
  }

  // ── Add item to alert feed ──
  function addFeedItem(alertData, dist, key) {
    // Remove empty state if present
    if (emptyFeed) emptyFeed.remove();

    const time = new Date(alertData.time).toLocaleTimeString("en-GB", {
      hour12: false,
    });
    const html = `
      <div class="atoa-feed-item" data-key="${key}">
        <div class="atoa-feed-icon ${dist < 1 ? "red" : "amber"}">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z"/>
          </svg>
        </div>
        <div class="atoa-feed-body">
          <div class="atoa-feed-title">Crash Alert — ${dist.toFixed(1)} km away</div>
          <div class="atoa-feed-meta mono">${alertData.lat.toFixed(5)}, ${alertData.lon.toFixed(5)} · ${time}</div>
        </div>
      </div>
    `;
    alertFeed.insertAdjacentHTML("afterbegin", html);
  }

  // ── Log crash to Flask backend ──
  function logCrashToServer() {
    fetch("/api/crash-alert/log", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        lat: currentLocation.lat,
        lon: currentLocation.lon,
        g_force: maxGForce,
        speed: currentSpeed,
        timestamp: Date.now(),
      }),
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.success && window.RoadSenseToast) {
          window.RoadSenseToast.show({
            type: "warning",
            title: "Crash logged",
            message: data.incident.incident_code,
            autoDismiss: 8000,
          });
        }
      })
      .catch((err) => console.error("Failed to log crash:", err));
  }

  // ── Speech Synthesis ──
  function speak(text) {
    if (!("speechSynthesis" in window)) return;
    const msg = new SpeechSynthesisUtterance(text);
    msg.rate = 0.95;
    msg.pitch = 1.1;
    window.speechSynthesis.speak(msg);
  }

  // ── Haversine distance (km) ──
  function getDistance(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const dLat = ((lat2 - lat1) * Math.PI) / 180;
    const dLon = ((lon2 - lon1) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos((lat1 * Math.PI) / 180) *
        Math.cos((lat2 * Math.PI) / 180) *
        Math.sin(dLon / 2) *
        Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  // ── Boot ──
  initFirebase();
})();
