/**
 * VE 아이디어 평가 매트릭스
 * 가중 평가 기준 × 대안 스코어링 + Chart.js 시각화
 */
(function () {
  const addIdeaBtn = document.getElementById('eval-add-idea');
  const addCriteriaBtn = document.getElementById('eval-add-criteria');
  const calcBtn = document.getElementById('eval-calc');
  const matrixEl = document.getElementById('eval-matrix');
  if (!addIdeaBtn || !matrixEl) return;

  const COLORS = ['#061E4A', '#3B82F6', '#10B981', '#F97316', '#EF4444', '#8B5CF6', '#06B6D4', '#D946EF'];

  // 기본 평가 기준 (가중치 포함)
  let criteria = [
    { name: '기술적 실현성', weight: 25 },
    { name: '비용 절감 효과', weight: 25 },
    { name: '공기 영향', weight: 15 },
    { name: '품질/성능 유지', weight: 20 },
    { name: '시공 용이성', weight: 15 },
  ];

  // 기본 아이디어
  let ideas = [
    { name: '대안 A: 공법 변경', scores: [4, 5, 3, 4, 4] },
    { name: '대안 B: 자재 대체', scores: [3, 4, 5, 3, 5] },
    { name: '대안 C: 설계 최적화', scores: [5, 3, 4, 5, 3] },
  ];

  let evalCharts = {};

  // ── 매트릭스 렌더링 ──
  function renderMatrix() {
    const totalWeight = criteria.reduce((s, c) => s + c.weight, 0);

    let html = `<table class="data-table" style="font-size:11px;min-width:600px;">
      <thead><tr>
        <th style="min-width:140px;">아이디어</th>
        ${criteria.map((c, ci) => `
          <th style="text-align:center;min-width:100px;">
            <input type="text" value="${c.name}" data-ci="${ci}" class="eval-crit-name"
              style="width:100%;border:none;background:transparent;font-size:10px;font-weight:600;text-align:center;color:var(--color-navy);outline:none;">
            <div style="margin-top:4px;">
              <span style="font-size:9px;color:var(--color-text-muted);">가중치:</span>
              <input type="number" value="${c.weight}" data-ci="${ci}" class="eval-crit-weight"
                style="width:36px;border:1px solid var(--color-border-mid);border-radius:2px;font-size:10px;text-align:center;padding:1px 2px;font-family:Outfit;">
              <span style="font-size:9px;color:var(--color-text-muted);">%</span>
            </div>
          </th>
        `).join('')}
        <th style="text-align:center;background:#EFF6FF;min-width:80px;">가중 점수</th>
        <th style="text-align:center;min-width:40px;"></th>
      </tr></thead>
      <tbody>
        ${ideas.map((idea, ii) => {
          const ws = calcWeightedScore(idea);
          return `<tr>
            <td>
              <input type="text" value="${idea.name}" data-ii="${ii}" class="eval-idea-name"
                style="width:100%;border:none;background:transparent;font-size:11px;font-weight:600;color:var(--color-navy);outline:none;">
            </td>
            ${criteria.map((c, ci) => `
              <td style="text-align:center;">
                <div style="display:flex;align-items:center;justify-content:center;gap:2px;">
                  ${[1,2,3,4,5].map(s => `
                    <span class="eval-star" data-ii="${ii}" data-ci="${ci}" data-score="${s}"
                      style="cursor:pointer;font-size:14px;color:${s <= idea.scores[ci] ? '#F59E0B' : '#E2E8F0'};">★</span>
                  `).join('')}
                </div>
                <div style="font-size:10px;font-family:Outfit;color:var(--color-text-muted);margin-top:2px;">${idea.scores[ci]}/5</div>
              </td>
            `).join('')}
            <td style="text-align:center;font-family:Outfit;font-size:16px;font-weight:700;color:${COLORS[ii % COLORS.length]};">${ws.toFixed(1)}</td>
            <td style="text-align:center;">
              <button class="eval-del-idea" data-ii="${ii}" style="border:none;background:none;color:#EF4444;cursor:pointer;font-size:14px;" title="삭제">×</button>
            </td>
          </tr>`;
        }).join('')}
      </tbody>
      <tfoot><tr>
        <td style="font-weight:600;color:var(--color-text-muted);font-size:10px;">가중치 합계</td>
        ${criteria.map(() => '<td></td>').join('')}
        <td style="text-align:center;font-family:Outfit;font-weight:700;font-size:12px;color:${totalWeight === 100 ? 'var(--color-emerald)' : 'var(--color-red)'};">${totalWeight}%</td>
        <td></td>
      </tr></tfoot>
    </table>`;

    matrixEl.innerHTML = html;
    bindMatrixEvents();
  }

  function calcWeightedScore(idea) {
    const totalWeight = criteria.reduce((s, c) => s + c.weight, 0);
    if (totalWeight === 0) return 0;
    return criteria.reduce((sum, c, ci) => sum + (idea.scores[ci] || 0) * (c.weight / totalWeight), 0);
  }

  function bindMatrixEvents() {
    // 별점 클릭
    matrixEl.querySelectorAll('.eval-star').forEach(star => {
      star.addEventListener('click', () => {
        const ii = parseInt(star.dataset.ii);
        const ci = parseInt(star.dataset.ci);
        const score = parseInt(star.dataset.score);
        ideas[ii].scores[ci] = score;
        renderMatrix();
      });
    });

    // 기준명 수정
    matrixEl.querySelectorAll('.eval-crit-name').forEach(input => {
      input.addEventListener('change', () => {
        criteria[parseInt(input.dataset.ci)].name = input.value;
      });
    });

    // 가중치 수정
    matrixEl.querySelectorAll('.eval-crit-weight').forEach(input => {
      input.addEventListener('change', () => {
        criteria[parseInt(input.dataset.ci)].weight = parseFloat(input.value) || 0;
        renderMatrix();
      });
    });

    // 아이디어명 수정
    matrixEl.querySelectorAll('.eval-idea-name').forEach(input => {
      input.addEventListener('change', () => {
        ideas[parseInt(input.dataset.ii)].name = input.value;
      });
    });

    // 삭제
    matrixEl.querySelectorAll('.eval-del-idea').forEach(btn => {
      btn.addEventListener('click', () => {
        ideas.splice(parseInt(btn.dataset.ii), 1);
        renderMatrix();
      });
    });
  }

  // ── 아이디어 추가 ──
  addIdeaBtn.addEventListener('click', () => {
    const n = ideas.length + 1;
    ideas.push({
      name: `대안 ${String.fromCharCode(64 + n)}: 새 아이디어`,
      scores: criteria.map(() => 3),
    });
    renderMatrix();
  });

  // ── 평가기준 추가 ──
  addCriteriaBtn.addEventListener('click', () => {
    const name = prompt('평가 기준명을 입력하세요:', '환경 영향');
    if (!name) return;
    const weight = parseInt(prompt('가중치(%)를 입력하세요:', '10')) || 10;
    criteria.push({ name, weight });
    ideas.forEach(idea => idea.scores.push(3));
    renderMatrix();
  });

  // ── 종합 평가 실행 ──
  calcBtn.addEventListener('click', () => {
    document.getElementById('eval-result').style.display = 'block';

    const scored = ideas.map((idea, i) => ({
      name: idea.name,
      total: calcWeightedScore(idea),
      scores: idea.scores,
      color: COLORS[i % COLORS.length],
    })).sort((a, b) => b.total - a.total);

    // 순위 차트
    requestAnimationFrame(() => {
      if (evalCharts.rank) evalCharts.rank.destroy();
      evalCharts.rank = new Chart(document.getElementById('eval-chart-rank'), {
        type: 'bar',
        data: {
          labels: scored.map((s, i) => `${i + 1}위 ${s.name}`),
          datasets: [{
            data: scored.map(s => s.total),
            backgroundColor: scored.map(s => s.color + 'CC'),
            borderRadius: 4, barThickness: 36,
          }],
        },
        options: {
          indexAxis: 'y',
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => ctx.raw.toFixed(2) + '점' } } },
          scales: {
            x: { min: 0, max: 5, ticks: { font: { family: 'Outfit', size: 10 } }, grid: { color: '#F1F5F9' } },
            y: { ticks: { font: { family: 'Pretendard', size: 10 } }, grid: { display: false } },
          },
        },
      });

      // 레이더 차트
      if (evalCharts.radar) evalCharts.radar.destroy();
      evalCharts.radar = new Chart(document.getElementById('eval-chart-radar'), {
        type: 'radar',
        data: {
          labels: criteria.map(c => c.name),
          datasets: ideas.map((idea, i) => ({
            label: idea.name,
            data: idea.scores,
            borderColor: COLORS[i % COLORS.length],
            backgroundColor: COLORS[i % COLORS.length] + '22',
            borderWidth: 2, pointRadius: 3,
          })),
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { position: 'bottom', labels: { font: { family: 'Pretendard', size: 10 } } } },
          scales: {
            r: {
              min: 0, max: 5,
              ticks: { stepSize: 1, font: { family: 'Outfit', size: 9 } },
              pointLabels: { font: { family: 'Pretendard', size: 10 } },
              grid: { color: '#E2E8F0' },
            },
          },
        },
      });
    });
  });

  // 초기 렌더링
  renderMatrix();
})();
