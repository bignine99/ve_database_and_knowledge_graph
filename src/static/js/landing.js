/* Landing page scroll reveal + counter animation */
document.addEventListener('DOMContentLoaded', function() {
  /* ── Scroll Reveal ── */
  const reveals = document.querySelectorAll('.reveal');
  const observer = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.15 });
  reveals.forEach(function(el) { observer.observe(el); });

  /* ── Counter Animation ── */
  const counters = document.querySelectorAll('.count-up');
  const cObserver = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      const target = parseInt(el.getAttribute('data-target'), 10);
      const suffix = el.getAttribute('data-suffix') || '';
      const duration = 2000;
      const start = performance.now();
      function tick(now) {
        const p = Math.min((now - start) / duration, 1);
        const ease = 1 - Math.pow(1 - p, 3);
        el.textContent = Math.floor(target * ease).toLocaleString() + suffix;
        if (p < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
      cObserver.unobserve(el);
    });
  }, { threshold: 0.5 });
  counters.forEach(function(el) { cObserver.observe(el); });

  /* ── Pipeline Sequential Highlight ── */
  var pipelineFlow = document.querySelector('.pipeline-flow');
  if (pipelineFlow) {
    var steps = pipelineFlow.querySelectorAll('.pipeline-step');
    var arrows = pipelineFlow.querySelectorAll('.pipeline-arrow');
    var pipelineRunning = false;
    var pipelineInterval = null;

    function runPipelineSequence() {
      if (pipelineRunning) return;
      pipelineRunning = true;
      var total = steps.length;
      var idx = 0;

      function activateStep() {
        /* Clear all */
        steps.forEach(function(s) { s.classList.remove('step-active'); });
        arrows.forEach(function(a) { a.classList.remove('arrow-active'); });

        if (idx < total) {
          /* Activate current step */
          steps[idx].classList.add('step-active');

          /* Activate the arrow BEFORE this step (the one leading to it) */
          if (idx > 0 && arrows[idx - 1]) {
            arrows[idx - 1].classList.add('arrow-active');
          }

          idx++;
          setTimeout(activateStep, 1000);
        } else {
          /* Brief pause at end, then reset and loop */
          setTimeout(function() {
            steps.forEach(function(s) { s.classList.remove('step-active'); });
            arrows.forEach(function(a) { a.classList.remove('arrow-active'); });
            idx = 0;
            setTimeout(activateStep, 800);
          }, 500);
        }
      }

      activateStep();
    }

    /* Trigger when pipeline scrolls into view */
    var pObserver = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (entry.isIntersecting) {
          runPipelineSequence();
          pObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.3 });
    pObserver.observe(pipelineFlow);
  }
});
