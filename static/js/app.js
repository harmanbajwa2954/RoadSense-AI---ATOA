/*
  app.js
  -------
  Shared, page-agnostic behaviors: live clock readout in the topbar and
  animated counters for stat cards (data-count-to attribute).
*/

(function () {
  function startClock() {
    const el = document.getElementById("topbar-clock");
    if (!el) return;
    function tick() {
      const now = new Date();
      const time = now.toLocaleTimeString("en-GB", { hour12: false });
      el.textContent = time;
    }
    tick();
    setInterval(tick, 1000);
  }

  function animateCounters() {
    const counters = document.querySelectorAll("[data-count-to]");
    counters.forEach((el) => {
      const target = parseFloat(el.getAttribute("data-count-to"));
      const decimals = el.getAttribute("data-decimals") ? parseInt(el.getAttribute("data-decimals"), 10) : 0;
      const duration = 900;
      const start = performance.now();

      function frame(now) {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        const value = target * eased;
        el.textContent = decimals ? value.toFixed(decimals) : Math.round(value).toLocaleString();
        if (progress < 1) requestAnimationFrame(frame);
      }
      requestAnimationFrame(frame);
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    startClock();
    animateCounters();
  });
})();
