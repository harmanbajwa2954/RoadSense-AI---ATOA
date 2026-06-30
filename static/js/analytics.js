/*
  analytics.js
  --------------
  Fetches /api/analytics/data and renders every Chart.js panel on the
  Analytics page. All charts are themed to match the dark ops-room palette
  via CSS variable lookups at render time.
*/

(function () {
  const canvasSigns = document.getElementById("chart-signs");
  if (!canvasSigns || typeof Chart === "undefined") return;

  const css = getComputedStyle(document.documentElement);
  const green = css.getPropertyValue("--signal-green").trim();
  const blue = css.getPropertyValue("--data-blue").trim();
  const amber = css.getPropertyValue("--alert-amber").trim();
  const red = css.getPropertyValue("--alert-red").trim();
  const violet = css.getPropertyValue("--violet").trim();
  const muted = css.getPropertyValue("--text-muted").trim();
  const hairline = css.getPropertyValue("--border-hairline").trim();

  Chart.defaults.color = muted;
  Chart.defaults.font.family = "'Inter', sans-serif";
  Chart.defaults.font.size = 11;

  const gridOpts = { color: hairline, borderColor: hairline };

  fetch("/api/analytics/data")
    .then((r) => r.json())
    .then(({ data }) => {
      new Chart(document.getElementById("chart-signs"), {
        type: "doughnut",
        data: {
          labels: data.traffic_sign_distribution.labels,
          datasets: [{ data: data.traffic_sign_distribution.values, backgroundColor: [green, blue, amber, red, violet, "#5b6478"], borderWidth: 0 }],
        },
        options: { plugins: { legend: { position: "bottom", labels: { boxWidth: 10 } } } },
      });

      new Chart(document.getElementById("chart-lane"), {
        type: "line",
        data: {
          labels: data.lane_detection_stats.labels,
          datasets: [
            { label: "Stable", data: data.lane_detection_stats.stable, borderColor: green, backgroundColor: "transparent", tension: 0.35 },
            { label: "Drifting", data: data.lane_detection_stats.drifting, borderColor: amber, backgroundColor: "transparent", tension: 0.35 },
          ],
        },
        options: { scales: { x: { grid: gridOpts }, y: { grid: gridOpts } }, plugins: { legend: { labels: { boxWidth: 10 } } } },
      });

      new Chart(document.getElementById("chart-hazards"), {
        type: "bar",
        data: { labels: data.road_hazard_stats.labels, datasets: [{ data: data.road_hazard_stats.values, backgroundColor: blue, borderRadius: 4 }] },
        options: { scales: { x: { grid: gridOpts }, y: { grid: gridOpts } }, plugins: { legend: { display: false } } },
      });

      new Chart(document.getElementById("chart-emergency"), {
        type: "bar",
        data: { labels: data.emergency_vehicle_trends.labels, datasets: [{ data: data.emergency_vehicle_trends.values, backgroundColor: red, borderRadius: 4 }] },
        options: { scales: { x: { grid: gridOpts }, y: { grid: gridOpts } }, plugins: { legend: { display: false } } },
      });

      new Chart(document.getElementById("chart-crash"), {
        type: "line",
        data: { labels: data.crash_trends.labels, datasets: [{ data: data.crash_trends.values, borderColor: red, backgroundColor: "rgba(255,71,87,0.12)", fill: true, tension: 0.35 }] },
        options: { scales: { x: { grid: gridOpts }, y: { grid: gridOpts } }, plugins: { legend: { display: false } } },
      });

      new Chart(document.getElementById("chart-safety"), {
        type: "radar",
        data: { labels: data.road_safety_index.labels, datasets: [{ data: data.road_safety_index.values, borderColor: green, backgroundColor: "rgba(21,216,138,0.15)" }] },
        options: { scales: { r: { grid: gridOpts, angleLines: { color: hairline }, pointLabels: { color: muted } } }, plugins: { legend: { display: false } } },
      });

      new Chart(document.getElementById("chart-inference"), {
        type: "bar",
        data: { labels: data.inference_statistics.labels, datasets: [{ data: data.inference_statistics.avg_ms, backgroundColor: violet, borderRadius: 4 }] },
        options: { indexAxis: "y", scales: { x: { grid: gridOpts }, y: { grid: gridOpts } }, plugins: { legend: { display: false } } },
      });
    });
})();
