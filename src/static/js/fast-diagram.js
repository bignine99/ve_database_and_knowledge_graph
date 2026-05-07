/**
 * FAST Diagram — AI 기반 기능 분해 + Mermaid 인터랙티브 렌더링
 * 표준 FAST: HOW? → SCOPE(WHAT) → WHY?
 */
(function () {
  const genBtn = document.getElementById('fast-gen-btn');
  const renderBtn = document.getElementById('fast-render-btn');
  const codeArea = document.getElementById('fast-code');
  const diagramArea = document.getElementById('fast-diagram-area');
  if (!genBtn) return;

  // Mermaid 초기화 — 큰 폰트, 넓은 간격
  if (typeof mermaid !== 'undefined') {
    mermaid.initialize({
      startOnLoad: false,
      theme: 'base',
      themeVariables: {
        primaryColor: '#E8F0FE',
        primaryBorderColor: '#1A365D',
        primaryTextColor: '#0F172A',
        lineColor: '#475569',
        secondaryColor: '#F1F5F9',
        tertiaryColor: '#FAFBFF',
        fontFamily: 'Pretendard, sans-serif',
        fontSize: '18px',
        nodeBorder: '2px',
      },
      flowchart: {
        htmlLabels: true,
        curve: 'linear',
        nodeSpacing: 60,
        rankSpacing: 80,
        padding: 34,
        useMaxWidth: true,
      },
    });
  }

  let renderCounter = 0;

  // ── Mermaid 렌더링 ──
  async function renderDiagram(code) {
    if (!code || !code.trim()) return;

    try {
      renderCounter++;
      const id = 'fast-mermaid-' + renderCounter;

      diagramArea.innerHTML = `
        <div style="margin-bottom:8px;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">
            <div>
              <div style="font-size:18px;font-weight:800;color:#0F172A;">FAST Diagram</div>
              <div style="font-size:11px;color:#94A3B8;margin-top:2px;">Function Analysis System Technique (Charles Bytheway)</div>
            </div>
            <div style="display:flex;gap:6px;align-items:center;">
              <span style="font-size:9px;background:#EFF6FF;color:#3B82F6;padding:3px 8px;border-radius:3px;font-weight:600;">AI Generated</span>
              <span style="font-size:9px;background:#ECFDF5;color:#10B981;padding:3px 8px;border-radius:3px;font-weight:600;">Mermaid v10</span>
            </div>
          </div>
          <!-- HOW / SCOPE / WHY 구간 표시 바 -->
          <div style="display:flex;align-items:stretch;height:36px;border-radius:5px;overflow:hidden;margin-bottom:6px;border:2px solid #1E293B;">
            <div style="flex:1;background:#1E3A5F;display:flex;align-items:center;justify-content:center;gap:6px;border-right:3px solid #F59E0B;">
              <span style="color:#F59E0B;font-size:16px;font-weight:900;">HOW?</span>
              <span style="color:#CBD5E1;font-size:10px;">→ 어떻게 달성하는가</span>
            </div>
            <div style="flex:1.5;background:#0F172A;display:flex;align-items:center;justify-content:center;gap:6px;">
              <span style="color:#F59E0B;font-size:11px;font-weight:700;">◀ SCOPE ▶</span>
              <span style="color:#94A3B8;font-size:10px;">기능 분석 범위 (WHAT)</span>
            </div>
            <div style="flex:1;background:#1E3A5F;display:flex;align-items:center;justify-content:center;gap:6px;border-left:3px solid #F59E0B;">
              <span style="color:#CBD5E1;font-size:10px;">왜 필요한가</span>
              <span style="color:#F59E0B;font-size:16px;font-weight:900;">WHY?</span>
            </div>
          </div>
          <!-- 범례 -->
          <div style="display:flex;gap:14px;flex-wrap:wrap;padding:6px 12px;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:4px;margin-bottom:10px;font-size:10px;color:#475569;">
            <span><span style="display:inline-block;width:14px;height:14px;background:#1E3A5F;border-radius:2px;vertical-align:middle;margin-right:3px;"></span> Basic Function</span>
            <span><span style="display:inline-block;width:14px;height:14px;background:#E8F0FE;border:2px solid #1A365D;border-radius:2px;vertical-align:middle;margin-right:3px;"></span> Critical Path</span>
            <span><span style="display:inline-block;width:16px;height:3px;background:#475569;vertical-align:middle;margin-right:3px;"></span> HOW/WHY</span>
            <span><span style="display:inline-block;width:16px;height:0;border-top:2px dashed #94A3B8;vertical-align:middle;margin-right:3px;"></span> When?/Supporting</span>
            <span>◇ Higher/Lower Order</span>
            <span>( ) Supporting Function</span>
          </div>
        </div>
        <div id="${id}" style="width:100%;overflow-x:auto;overflow-y:auto;"></div>
      `;

      const { svg } = await mermaid.render(id + '-svg', code);
      document.getElementById(id).innerHTML = svg;

      // SVG 화면 전체에 꽉 차도록
      const svgEl = document.getElementById(id).querySelector('svg');
      if (svgEl) {
        svgEl.style.width = '100%';
        svgEl.style.height = 'auto';
        svgEl.style.minHeight = '500px';
        svgEl.removeAttribute('height');
        // viewBox 유지하여 스케일 자동 조정
      }
    } catch (e) {
      diagramArea.innerHTML = `
        <div style="padding:40px;text-align:center;color:#EF4444;">
          <div style="font-size:14px;font-weight:600;margin-bottom:8px;">렌더링 오류</div>
          <div style="font-size:11px;line-height:1.6;">${e.message || e}</div>
          <div style="margin-top:12px;font-size:10px;color:#94A3B8;">Mermaid 코드를 수정한 후 "다시 렌더링"을 클릭하세요.</div>
        </div>`;
    }
  }

  // ── AI 생성 ──
  genBtn.addEventListener('click', async () => {
    const project = document.getElementById('fast-project').value.trim();
    if (!project) { alert('프로젝트/시설명을 입력하세요.'); return; }

    genBtn.disabled = true;
    genBtn.textContent = '🔄 AI 생성 중...';
    diagramArea.innerHTML = `
      <div style="text-align:center;padding:60px;color:#94A3B8;">
        <div style="font-size:32px;margin-bottom:12px;animation:pulse 1.5s infinite;">🧠</div>
        <div style="font-size:14px;font-weight:600;">Gemini가 표준 FAST Diagram을 분석 중...</div>
        <div style="font-size:11px;margin-top:6px;color:#CBD5E1;">HOW? → SCOPE(WHAT) → WHY? 구조 생성</div>
      </div>`;

    try {
      const res = await fetch('/api/ve/fast-diagram', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project,
          higher_function: document.getElementById('fast-higher').value.trim(),
          description: document.getElementById('fast-desc').value.trim(),
        }),
      });
      const data = await res.json();

      if (data.error) {
        diagramArea.innerHTML = `<div style="padding:40px;text-align:center;color:#EF4444;">오류: ${data.error}</div>`;
        return;
      }

      const code = data.mermaid_code || '';
      codeArea.value = code;
      await renderDiagram(code);
    } catch (e) {
      diagramArea.innerHTML = `<div style="padding:40px;text-align:center;color:#EF4444;">네트워크 오류: ${e.message}</div>`;
    } finally {
      genBtn.disabled = false;
      genBtn.textContent = '🧠 AI FAST Diagram 생성';
    }
  });

  // ── 수동 렌더링 ──
  renderBtn.addEventListener('click', () => {
    const code = codeArea.value.trim();
    if (code) renderDiagram(code);
  });
})();
