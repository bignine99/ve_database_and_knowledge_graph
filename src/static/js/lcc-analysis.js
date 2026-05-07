/**
 * LCC (Life Cycle Cost) 비교 분석 — 원안 vs 대안
 * NPV 할인법 기반 생애주기비용 산출 + Chart.js 시각화
 */
(function () {
  const calcBtn = document.getElementById('lcc-calc-btn');
  if (!calcBtn) return;

  const COLORS = {
    navy: '#061E4A', accent: '#3B82F6', emerald: '#10B981',
    orange: '#F97316', red: '#EF4444', neutral: '#64748B',
  };

  let lccCharts = {};

  function getVal(id) { return parseFloat(document.getElementById(id).value) || 0; }

  calcBtn.addEventListener('click', () => {
    const period = Math.max(10, Math.min(60, getVal('lcc-period')));
    const rate = getVal('lcc-rate') / 100;
    const altName = document.getElementById('lcc-alt-name').value || 'VE 대안';

    // 비용 데이터 수집
    const orig = {
      init: getVal('lcc-orig-init'), design: getVal('lcc-orig-design'),
      maint: getVal('lcc-orig-maint'), energy: getVal('lcc-orig-energy'),
      replace: getVal('lcc-orig-replace'), repCycle: getVal('lcc-orig-repcycle') || 15,
      demo: getVal('lcc-orig-demo'),
    };
    const alt = {
      init: getVal('lcc-alt-init'), design: getVal('lcc-alt-design'),
      maint: getVal('lcc-alt-maint'), energy: getVal('lcc-alt-energy'),
      replace: getVal('lcc-alt-replace'), repCycle: getVal('lcc-alt-repcycle') || 20,
      demo: getVal('lcc-alt-demo'),
    };

    // NPV 계산
    function calcLCC(c) {
      const annual = []; // 연도별 비용 (현재가)
      const nominal = []; // 연도별 비용 (명목가)
      let totalInit = c.init + c.design;

      for (let y = 0; y <= period; y++) {
        const df = Math.pow(1 + rate, y); // 할인계수
        let cost = 0;
        if (y === 0) cost = totalInit;
        else {
          cost += c.maint + c.energy;
          if (c.repCycle > 0 && y % c.repCycle === 0 && y < period) cost += c.replace;
          if (y === period) cost += c.demo;
        }
        nominal.push(cost);
        annual.push(cost / df);
      }

      const totalNPV = annual.reduce((s, v) => s + v, 0);

      // 항목별 NPV
      const initNPV = totalInit;
      let maintNPV = 0, energyNPV = 0, replaceNPV = 0, demoNPV = 0;
      for (let y = 1; y <= period; y++) {
        const df = Math.pow(1 + rate, y);
        maintNPV += c.maint / df;
        energyNPV += c.energy / df;
        if (c.repCycle > 0 && y % c.repCycle === 0 && y < period) replaceNPV += c.replace / df;
        if (y === period) demoNPV += c.demo / df;
      }

      return { annual, nominal, totalNPV, initNPV, maintNPV, energyNPV, replaceNPV, demoNPV };
    }

    const origLCC = calcLCC(orig);
    const altLCC = calcLCC(alt);
    const savings = origLCC.totalNPV - altLCC.totalNPV;
    const savingsRate = origLCC.totalNPV > 0 ? (savings / origLCC.totalNPV * 100) : 0;

    // 누적 비용
    const origCum = [], altCum = [];
    let oc = 0, ac = 0;
    for (let y = 0; y <= period; y++) {
      oc += origLCC.annual[y]; ac += altLCC.annual[y];
      origCum.push(oc); altCum.push(ac);
    }

    // BEP (Break-Even Point)
    let bep = '-';
    if (alt.init + alt.design > orig.init + orig.design) {
      for (let y = 1; y <= period; y++) {
        if (altCum[y] <= origCum[y]) { bep = y + '년차'; break; }
      }
    } else {
      bep = '즉시';
    }

    // UI 표시
    document.getElementById('lcc-results').style.display = 'block';
    document.getElementById('lcc-placeholder').style.display = 'none';

    // KPI
    const fmt = v => Math.round(v).toLocaleString('ko-KR');
    document.getElementById('lcc-kpi-row').innerHTML = `
      <div class="kpi-card"><div class="kpi-label">원안 LCC (NPV)</div><div class="kpi-value">${fmt(origLCC.totalNPV)}</div><div class="kpi-sub">백만원 · ${period}년</div></div>
      <div class="kpi-card"><div class="kpi-label">${altName} LCC (NPV)</div><div class="kpi-value" style="color:${COLORS.accent}">${fmt(altLCC.totalNPV)}</div><div class="kpi-sub">백만원 · ${period}년</div></div>
      <div class="kpi-card"><div class="kpi-label">LCC 절감액</div><div class="kpi-value" style="color:${savings >= 0 ? COLORS.emerald : COLORS.red}">${savings >= 0 ? '+' : ''}${fmt(savings)}</div><div class="kpi-sub">백만원 (${savingsRate.toFixed(1)}%)</div></div>
      <div class="kpi-card"><div class="kpi-label">BEP (손익분기)</div><div class="kpi-value">${bep}</div><div class="kpi-sub">투자 회수 시점</div></div>
    `;

    // 차트 공통 옵션
    const years = Array.from({ length: period + 1 }, (_, i) => i + '년');
    const chartFont = { family: 'Outfit', size: 10 };

    // 1. LCC 총액 비교 (Bar)
    if (lccCharts.total) lccCharts.total.destroy();
    lccCharts.total = new Chart(document.getElementById('lcc-chart-total'), {
      type: 'bar',
      data: {
        labels: ['원안', altName],
        datasets: [{
          data: [origLCC.totalNPV, altLCC.totalNPV],
          backgroundColor: [COLORS.navy + 'CC', COLORS.accent + 'CC'],
          borderRadius: 4, barThickness: 60,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: ctx => fmt(ctx.raw) + '백만원' } },
        },
        scales: {
          y: { ticks: { font: chartFont, callback: v => fmt(v) }, grid: { color: '#F1F5F9' } },
          x: { ticks: { font: { family: 'Pretendard', size: 12, weight: 600 } }, grid: { display: false } },
        },
      },
    });

    // 2. 항목별 비용 구성 (Stacked Bar)
    if (lccCharts.breakdown) lccCharts.breakdown.destroy();
    const cats = ['초기투자', '유지관리', '에너지', '교체비', '철거비'];
    lccCharts.breakdown = new Chart(document.getElementById('lcc-chart-breakdown'), {
      type: 'bar',
      data: {
        labels: ['원안', altName],
        datasets: [
          { label: '초기투자', data: [origLCC.initNPV, altLCC.initNPV], backgroundColor: COLORS.navy },
          { label: '유지관리', data: [origLCC.maintNPV, altLCC.maintNPV], backgroundColor: COLORS.accent },
          { label: '에너지', data: [origLCC.energyNPV, altLCC.energyNPV], backgroundColor: COLORS.emerald },
          { label: '교체비', data: [origLCC.replaceNPV, altLCC.replaceNPV], backgroundColor: COLORS.orange },
          { label: '철거비', data: [origLCC.demoNPV, altLCC.demoNPV], backgroundColor: COLORS.neutral },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { font: { family: 'Pretendard', size: 10 }, padding: 8 } },
          tooltip: { callbacks: { label: ctx => ctx.dataset.label + ': ' + fmt(ctx.raw) + '백만원' } },
        },
        scales: {
          x: { stacked: true, ticks: { font: { family: 'Pretendard', size: 12, weight: 600 } }, grid: { display: false } },
          y: { stacked: true, ticks: { font: chartFont, callback: v => fmt(v) }, grid: { color: '#F1F5F9' } },
        },
      },
    });

    // 3. 누적 비용 추이 (Line)
    if (lccCharts.cumulative) lccCharts.cumulative.destroy();
    lccCharts.cumulative = new Chart(document.getElementById('lcc-chart-cumulative'), {
      type: 'line',
      data: {
        labels: years,
        datasets: [
          { label: '원안', data: origCum, borderColor: COLORS.navy, backgroundColor: COLORS.navy + '11', borderWidth: 2, fill: true, tension: 0.3, pointRadius: 0 },
          { label: altName, data: altCum, borderColor: COLORS.accent, backgroundColor: COLORS.accent + '11', borderWidth: 2, fill: true, tension: 0.3, pointRadius: 0 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { font: { family: 'Pretendard', size: 10 } } },
          tooltip: { callbacks: { label: ctx => ctx.dataset.label + ': ' + fmt(ctx.raw) + '백만원' } },
        },
        scales: {
          x: { ticks: { font: chartFont, maxTicksLimit: 10 }, grid: { display: false } },
          y: { ticks: { font: chartFont, callback: v => fmt(v) }, grid: { color: '#F1F5F9' } },
        },
      },
    });

    // 4. 연도별 비용 흐름 (Bar)
    if (lccCharts.annual) lccCharts.annual.destroy();
    lccCharts.annual = new Chart(document.getElementById('lcc-chart-annual'), {
      type: 'bar',
      data: {
        labels: years,
        datasets: [
          { label: '원안', data: origLCC.annual, backgroundColor: COLORS.navy + '77', borderRadius: 1 },
          { label: altName, data: altLCC.annual, backgroundColor: COLORS.accent + '77', borderRadius: 1 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { font: { family: 'Pretendard', size: 10 } } },
          tooltip: { callbacks: { label: ctx => ctx.dataset.label + ': ' + fmt(ctx.raw) + '백만원' } },
        },
        scales: {
          x: { ticks: { font: chartFont, maxTicksLimit: 15 }, grid: { display: false } },
          y: { ticks: { font: chartFont, callback: v => fmt(v) }, grid: { color: '#F1F5F9' } },
        },
      },
    });

    // 상세 테이블
    const table = document.getElementById('lcc-detail-table');
    table.querySelector('thead').innerHTML = `<tr>
      <th>연도</th><th>원안 명목비용</th><th>원안 현재가</th><th>원안 누적(NPV)</th>
      <th>${altName} 명목비용</th><th>${altName} 현재가</th><th>${altName} 누적(NPV)</th><th>절감액(누적)</th>
    </tr>`;
    let rows = '';
    for (let y = 0; y <= period; y++) {
      const diff = origCum[y] - altCum[y];
      rows += `<tr style="${y === 0 || y === period ? 'font-weight:600;' : ''}">
        <td style="font-family:Outfit;color:${COLORS.navy};">${y}년</td>
        <td style="font-family:Outfit;text-align:right;">${fmt(origLCC.nominal[y])}</td>
        <td style="font-family:Outfit;text-align:right;">${fmt(origLCC.annual[y])}</td>
        <td style="font-family:Outfit;text-align:right;font-weight:600;">${fmt(origCum[y])}</td>
        <td style="font-family:Outfit;text-align:right;color:${COLORS.accent};">${fmt(altLCC.nominal[y])}</td>
        <td style="font-family:Outfit;text-align:right;color:${COLORS.accent};">${fmt(altLCC.annual[y])}</td>
        <td style="font-family:Outfit;text-align:right;font-weight:600;color:${COLORS.accent};">${fmt(altCum[y])}</td>
        <td style="font-family:Outfit;text-align:right;color:${diff >= 0 ? COLORS.emerald : COLORS.red};font-weight:600;">${diff >= 0 ? '+' : ''}${fmt(diff)}</td>
      </tr>`;
    }
    table.querySelector('tbody').innerHTML = rows;
  });
})();
