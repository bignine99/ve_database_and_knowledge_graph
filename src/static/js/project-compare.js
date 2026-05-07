/**
 * 프로젝트 비교 — 공사/프로젝트유형 필터 → 프로젝트 선택 → 벤치마킹
 */
(function () {
  const runBtn = document.getElementById('cmp-run-btn');
  if (!runBtn) return;

  const COLORS = ['#061E4A', '#3B82F6', '#10B981'];
  const COLORS_LIGHT = ['#061E4A99', '#3B82F699', '#10B98199'];
  const HOW1_MAP = {
    'A': '건축공사', 'B': '토목공사', 'C': '조경공사',
    'D': '기계설비공사', 'E': '전기공사', 'F': '소방공사',
    'G': '통신공사',
  };

  // 프로젝트명에서 유형을 추출하는 키워드 매핑
  const TYPE_KEYWORDS = [
    { type: '학교', keywords: ['학교', '초등', '중학', '고등', '대학', '교육', '캠퍼스'] },
    { type: '공동주택', keywords: ['아파트', '공동주택', '주택', '주거', '빌라', '연립'] },
    { type: '체육시설', keywords: ['체육', '스포츠', '수영', '경기장', '운동'] },
    { type: '철도/교통', keywords: ['철도', '전철', '지하철', '도시철도', '차량기지', '역사', '급행'] },
    { type: '도로/교량', keywords: ['도로', '교량', '터널', '고속', '인터체인지'] },
    { type: '의료시설', keywords: ['병원', '의료', '보건', '클리닉'] },
    { type: '문화시설', keywords: ['문화', '도서관', '박물관', '미술관', '공연'] },
    { type: '업무시설', keywords: ['청사', '관공서', '사무', '오피스', '센터'] },
    { type: '소방시설', keywords: ['소방', '119', '방재'] },
    { type: '공공시설', keywords: ['공공', '복지', '커뮤니티', '마을'] },
    { type: '사례집', keywords: ['사례집', '사례', '제안유형'] },
  ];

  function classifyProject(pname, location) {
    const text = (pname || '') + ' ' + (location || '');
    for (const { type, keywords } of TYPE_KEYWORDS) {
      if (keywords.some(kw => text.includes(kw))) return type;
    }
    return '기타';
  }

  let cmpCharts = {};
  let rawData = null;
  let filteredProjects = {};

  const filterHow1 = document.getElementById('cmp-filter-how1');
  const filterField = document.getElementById('cmp-filter-field');
  const filterCount = document.getElementById('cmp-filter-count');

  // ── 데이터 로드 ──
  async function loadData() {
    if (rawData) return;
    try {
      const res = await fetch('/api/alternatives');
      rawData = await res.json();
    } catch { rawData = []; }

    // 각 대안에 프로젝트 유형 추가
    rawData.forEach(a => {
      a._projType = classifyProject(a.pname, a.location);
    });

    // 필터 옵션 생성
    const how1Set = new Set();
    const typeSet = new Set();

    rawData.forEach(a => {
      const h = (a.how2_code || '').split('-')[0];
      if (h && HOW1_MAP[h]) how1Set.add(h);
      typeSet.add(a._projType);
    });

    // 공사 필터
    [...how1Set].sort().forEach(h => {
      const opt = document.createElement('option');
      opt.value = h;
      opt.textContent = HOW1_MAP[h] || h;
      filterHow1.appendChild(opt);
    });

    // 프로젝트 유형 필터
    [...typeSet].sort().forEach(t => {
      const opt = document.createElement('option');
      opt.value = t;
      opt.textContent = t;
      filterField.appendChild(opt);
    });

    applyFilter();
  }

  // ── 필터 적용 → 프로젝트 드롭다운 갱신 ──
  function applyFilter() {
    const selHow1 = filterHow1.value;
    const selField = filterField.value;

    // 필터링
    let filtered = rawData;
    if (selHow1) {
      filtered = filtered.filter(a => (a.how2_code || '').startsWith(selHow1 + '-') || (a.how2_code || '').startsWith(selHow1));
    }
    if (selField) {
      filtered = filtered.filter(a => a._projType === selField);
    }

    // location 기반 프로젝트 그룹화
    filteredProjects = {};
    filtered.forEach(a => {
      const loc = a.location || '미분류';
      if (!filteredProjects[loc]) filteredProjects[loc] = [];
      filteredProjects[loc].push(a);
    });

    // 프로젝트 드롭다운 갱신
    const sorted = Object.entries(filteredProjects).sort((a, b) => b[1].length - a[1].length);
    const selects = ['cmp-proj-1', 'cmp-proj-2', 'cmp-proj-3'];

    selects.forEach((id, idx) => {
      const el = document.getElementById(id);
      el.innerHTML = `<option value="">-- 프로젝트 ${String.fromCharCode(65 + idx)} ${idx === 2 ? '(선택)' : ''} --</option>`;
      sorted.forEach(([loc, alts]) => {
        const opt = document.createElement('option');
        opt.value = loc;
        opt.textContent = `${loc} (${alts.length}건)`;
        el.appendChild(opt);
      });
    });

    // 카운트 표시
    const filterLabel = [];
    if (selHow1) filterLabel.push(HOW1_MAP[selHow1]);
    if (selField) filterLabel.push(selField);
    filterCount.textContent = `${filterLabel.length ? filterLabel.join(' · ') + ' → ' : ''}${filtered.length}건 / ${Object.keys(filteredProjects).length}개 프로젝트`;
  }

  // 필터 변경 이벤트
  filterHow1.addEventListener('change', applyFilter);
  filterField.addEventListener('change', applyFilter);

  // 네비게이션 진입 시 로드
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      if (item.dataset.page === 'compare') setTimeout(loadData, 100);
    });
  });

  // ── 비교 실행 ──
  runBtn.addEventListener('click', async () => {
    await loadData();

    const sel1 = document.getElementById('cmp-proj-1').value;
    const sel2 = document.getElementById('cmp-proj-2').value;
    const sel3 = document.getElementById('cmp-proj-3').value;

    const selected = [sel1, sel2, sel3].filter(Boolean);
    if (selected.length < 2) { alert('최소 2개 프로젝트를 선택하세요.'); return; }

    const analyses = selected.map(loc => analyze(filteredProjects[loc] || [], loc));

    document.getElementById('cmp-results').style.display = 'block';
    document.getElementById('cmp-placeholder').style.display = 'none';

    renderKPI(analyses);
    requestAnimationFrame(() => renderCharts(analyses));
    renderTable(analyses);
  });

  function analyze(alts, name) {
    const total = alts.length;
    const savings = alts.filter(a => a.savings_rate != null).map(a => parseFloat(a.savings_rate) || 0);
    const avgSavings = savings.length ? savings.reduce((s, v) => s + v, 0) / savings.length : 0;
    const maxSavings = savings.length ? Math.max(...savings) : 0;

    const how1 = {};
    alts.forEach(a => {
      const code = (a.how2_code || '').split('-')[0] || '기타';
      const label = HOW1_MAP[code] || code;
      how1[label] = (how1[label] || 0) + 1;
    });

    const vtype = {};
    alts.forEach(a => {
      const t = a.value_type || '미분류';
      vtype[t] = (vtype[t] || 0) + 1;
    });

    return { name, total, avgSavings, maxSavings, how1, vtype };
  }

  function renderKPI(analyses) {
    const fmt = v => v.toFixed(1);
    document.getElementById('cmp-kpi').innerHTML = analyses.map((a, i) => `
      <div class="kpi-card" style="border-bottom-color:${COLORS[i]};">
        <div class="kpi-label" style="color:${COLORS[i]};">${a.name}</div>
        <div class="kpi-value" style="color:${COLORS[i]};">${a.total}</div>
        <div class="kpi-sub">대안 ${a.total}건 · 평균절감 ${fmt(a.avgSavings)}% · 최대 ${fmt(a.maxSavings)}%</div>
      </div>
    `).join('');
  }

  function renderCharts(analyses) {
    const labels = analyses.map(a => a.name);
    const chartFont = { family: 'Outfit', size: 10 };

    if (cmpCharts.count) cmpCharts.count.destroy();
    cmpCharts.count = new Chart(document.getElementById('cmp-chart-count'), {
      type: 'bar',
      data: { labels, datasets: [{ data: analyses.map(a => a.total), backgroundColor: COLORS.slice(0, analyses.length), borderRadius: 4, barThickness: 50 }] },
      options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } },
        scales: { y: { ticks: { font: chartFont }, grid: { color: '#F1F5F9' } }, x: { ticks: { font: { family: 'Pretendard', size: 11 } }, grid: { display: false } } } },
    });

    if (cmpCharts.savings) cmpCharts.savings.destroy();
    cmpCharts.savings = new Chart(document.getElementById('cmp-chart-savings'), {
      type: 'bar',
      data: { labels, datasets: [
        { label: '평균 절감율', data: analyses.map(a => a.avgSavings), backgroundColor: COLORS_LIGHT.slice(0, analyses.length), borderRadius: 4, barThickness: 40 },
        { label: '최대 절감율', data: analyses.map(a => a.maxSavings), backgroundColor: COLORS.slice(0, analyses.length), borderRadius: 4, barThickness: 40 },
      ] },
      options: { responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { font: { family: 'Pretendard', size: 10 } } } },
        scales: { y: { ticks: { font: chartFont, callback: v => v + '%' }, grid: { color: '#F1F5F9' } }, x: { ticks: { font: { family: 'Pretendard', size: 11 } }, grid: { display: false } } } },
    });

    const allHow1 = [...new Set(analyses.flatMap(a => Object.keys(a.how1)))];
    if (cmpCharts.how1) cmpCharts.how1.destroy();
    cmpCharts.how1 = new Chart(document.getElementById('cmp-chart-how1'), {
      type: 'bar',
      data: { labels: allHow1, datasets: analyses.map((a, i) => ({ label: a.name, data: allHow1.map(h => a.how1[h] || 0), backgroundColor: COLORS[i] + 'AA', borderRadius: 2 })) },
      options: { responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { font: { family: 'Pretendard', size: 10 } } } },
        scales: { y: { ticks: { font: chartFont }, grid: { color: '#F1F5F9' } }, x: { ticks: { font: { family: 'Pretendard', size: 9 } }, grid: { display: false } } } },
    });

    const allVtype = [...new Set(analyses.flatMap(a => Object.keys(a.vtype)))];
    if (cmpCharts.vtype) cmpCharts.vtype.destroy();
    cmpCharts.vtype = new Chart(document.getElementById('cmp-chart-vtype'), {
      type: 'bar',
      data: { labels: allVtype, datasets: analyses.map((a, i) => ({ label: a.name, data: allVtype.map(v => a.vtype[v] || 0), backgroundColor: COLORS[i] + 'AA', borderRadius: 2 })) },
      options: { responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { font: { family: 'Pretendard', size: 10 } } } },
        scales: { y: { ticks: { font: chartFont }, grid: { color: '#F1F5F9' } }, x: { ticks: { font: { family: 'Pretendard', size: 9 } }, grid: { display: false } } } },
    });
  }

  function renderTable(analyses) {
    const table = document.getElementById('cmp-detail-table');
    table.querySelector('thead').innerHTML = `<tr>
      <th>지표</th>${analyses.map((a, i) => `<th style="color:${COLORS[i]};">${a.name}</th>`).join('')}
    </tr>`;

    const rows = [
      ['총 대안 수', ...analyses.map(a => a.total + '건')],
      ['평균 절감율', ...analyses.map(a => a.avgSavings.toFixed(2) + '%')],
      ['최대 절감율', ...analyses.map(a => a.maxSavings.toFixed(2) + '%')],
      ['주요 공종', ...analyses.map(a => {
        const sorted = Object.entries(a.how1).sort((x, y) => y[1] - x[1]);
        return sorted.slice(0, 2).map(([k, v]) => `${k}(${v})`).join(', ');
      })],
      ['주요 가치유형', ...analyses.map(a => {
        const sorted = Object.entries(a.vtype).sort((x, y) => y[1] - x[1]);
        return sorted.slice(0, 2).map(([k, v]) => `${k}(${v})`).join(', ');
      })],
    ];

    table.querySelector('tbody').innerHTML = rows.map(r =>
      `<tr><td style="font-weight:600;color:var(--color-navy);">${r[0]}</td>${r.slice(1).map(v => `<td style="font-family:Outfit;">${v}</td>`).join('')}</tr>`
    ).join('');
  }
})();
