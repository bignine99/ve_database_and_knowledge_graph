/**
 * VE Report Generator — 라운드테이블 결과를 보고서로 자동 생성
 */
(function () {
  const selectEl = document.getElementById('rpt-session-select');
  const infoEl = document.getElementById('rpt-session-info');
  const genBtn = document.getElementById('rpt-generate-btn');
  const printBtn = document.getElementById('rpt-print-btn');
  const preview = document.getElementById('rpt-preview');
  if (!selectEl || !genBtn) return;

  let sessionsCache = {};

  // ── 페이지 진입 시 세션 목록 로드 ──
  async function loadSessions() {
    try {
      const res = await fetch('/api/ve/roundtable/sessions');
      const data = await res.json();
      selectEl.innerHTML = '<option value="">-- 세션을 선택하세요 --</option>';
      (data.sessions || []).forEach(s => {
        sessionsCache[s.session_id] = s;
        const d = new Date(s.created_at * 1000);
        const timeStr = d.toLocaleString('ko-KR', { hour: '2-digit', minute: '2-digit' });
        const statusLabel = s.status === 'completed' ? '✅' : s.status === 'running' ? '⏳' : '❌';
        const opt = document.createElement('option');
        opt.value = s.session_id;
        opt.textContent = `${statusLabel} ${s.project_name} (${s.message_count}건, ${timeStr})`;
        selectEl.appendChild(opt);
      });
    } catch (e) { /* silent */ }
  }

  // 네비게이션에서 report 탭 클릭 시 세션 목록 새로고침
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      if (item.dataset.page === 'report') setTimeout(loadSessions, 100);
    });
  });

  // ── 세션 선택 ──
  selectEl.addEventListener('change', () => {
    const sid = selectEl.value;
    if (!sid) {
      infoEl.style.display = 'none';
      genBtn.disabled = true;
      return;
    }
    const s = sessionsCache[sid];
    if (s) {
      infoEl.style.display = 'block';
      infoEl.innerHTML =
        '<strong>' + s.project_name + '</strong><br>' +
        '상태: ' + (s.status === 'completed' ? '✅ 완료' : s.status) + '<br>' +
        '메시지: ' + s.message_count + '건';
      genBtn.disabled = s.status !== 'completed';
    }
  });

  // ── 보고서 생성 ──
  genBtn.addEventListener('click', async () => {
    const sid = selectEl.value;
    if (!sid) return;
    genBtn.disabled = true;
    genBtn.textContent = '생성 중...';

    try {
      const res = await fetch(`/api/ve/roundtable/${sid}/messages?since=0`);
      const data = await res.json();

      if (!data.new_messages || data.new_messages.length === 0) {
        preview.innerHTML = '<div style="padding:40px;text-align:center;color:#94a3b8;">메시지가 없습니다.</div>';
        return;
      }

      const s = sessionsCache[sid] || {};
      const messages = data.new_messages;
      const now = new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' });

      // ── 보고서 콘텐츠 생성 ──
      let html = '';

      // 표지
      html += `<div style="padding:60px 50px 40px;border-bottom:3px solid #061E4A;">
        <div style="text-align:center;">
          <div style="font-size:10px;font-weight:700;color:#3B82F6;letter-spacing:0.2em;text-transform:uppercase;margin-bottom:8px;">VE Workshop Report</div>
          <h1 style="font-size:26px;font-weight:700;color:#061E4A;margin:0 0 8px;line-height:1.3;">${escHtml(s.project_name || 'VE 분석 보고서')}</h1>
          <div style="font-size:12px;color:#64748B;margin-bottom:24px;">Value Engineering Roundtable Analysis Report</div>
          <div style="display:flex;justify-content:center;gap:24px;font-size:11px;color:#94A3B8;">
            <span>📅 ${now}</span>
            <span>💬 ${messages.length}건 토론</span>
            <span>👥 ${countAgents(messages)}명 참여</span>
          </div>
        </div>
      </div>`;

      // 목차
      html += `<div style="padding:30px 50px;border-bottom:1px solid #E2E8F0;">
        <h2 style="font-size:14px;font-weight:700;color:#061E4A;margin:0 0 12px;">📋 목차</h2>
        <div style="font-size:12px;color:#475569;line-height:2;">
          1. 프로젝트 개요 및 회의 배경<br>
          2. 참여 전문가 현황<br>
          3. 1차 전문가 검토 의견<br>
          4. VE 아이디어 제안<br>
          5. FAST 기능 분석<br>
          6. 2차 피드백 및 검증<br>
          7. 종합 결론 및 향후 계획
        </div>
      </div>`;

      // 참여자 현황
      const agentMap = {};
      messages.forEach(m => {
        if (!agentMap[m.agent_id]) agentMap[m.agent_id] = { name: m.agent_name, emoji: m.agent_emoji, color: m.agent_color, count: 0 };
        agentMap[m.agent_id].count++;
      });

      html += `<div style="padding:30px 50px;border-bottom:1px solid #E2E8F0;">
        <h2 style="font-size:14px;font-weight:700;color:#061E4A;margin:0 0 16px;">2. 참여 전문가 현황</h2>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;">
          ${Object.values(agentMap).map(a => `
            <div style="border:1px solid #E2E8F0;border-radius:6px;padding:12px;text-align:center;border-left:3px solid ${a.color};">
              <div style="font-size:20px;margin-bottom:4px;">${a.emoji}</div>
              <div style="font-size:11px;font-weight:600;color:#061E4A;">${a.name}</div>
              <div style="font-size:10px;color:#94A3B8;">${a.count}회 발언</div>
            </div>
          `).join('')}
        </div>
      </div>`;

      // Step별 메시지 그룹화
      const stepGroups = {};
      messages.forEach(m => {
        if (!stepGroups[m.step]) stepGroups[m.step] = [];
        stepGroups[m.step].push(m);
      });

      const stepTitles = {
        1: '1. 프로젝트 개요 및 회의 배경',
        2: '3. 1차 전문가 검토 의견',
        3: '3-1. 데이터 분석 — 유사 사례 검색',
        4: '4. VE 아이디어 제안',
        5: '5. FAST 기능 분석',
        6: '6-1. 2차 전문가 피드백',
        7: '6-2. 데이터 기반 검증',
        8: '6-3. 최종 아이디어 정리',
        9: '6-4. 기능-비용 최종 평가',
        10: '7. 종합 결론 및 향후 계획',
      };

      // 각 Step 렌더링
      Object.keys(stepGroups).sort((a, b) => a - b).forEach(step => {
        const msgs = stepGroups[step];
        const title = stepTitles[step] || `Step ${step}`;
        const isSummary = parseInt(step) === 10;

        html += `<div style="padding:30px 50px;border-bottom:1px solid #E2E8F0;${isSummary ? 'background:#FAFBFF;' : ''}">
          <h2 style="font-size:14px;font-weight:700;color:#061E4A;margin:0 0 16px;">${title}</h2>`;

        msgs.forEach(m => {
          const formatted = formatContent(m.content);
          html += `<div style="margin-bottom:16px;padding:14px 16px;background:#F8FAFC;border-radius:6px;border-left:3px solid ${m.agent_color};">
            <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px;">
              <span style="font-size:14px;">${m.agent_emoji}</span>
              <span style="font-size:11px;font-weight:700;color:${m.agent_color};">${m.agent_name}</span>
            </div>
            <div style="font-size:12px;line-height:1.8;color:#1E293B;">${formatted}</div>
          </div>`;
        });

        html += '</div>';
      });

      // 푸터
      html += `<div style="padding:24px 50px;text-align:center;font-size:10px;color:#94A3B8;">
        <div style="margin-bottom:4px;">VE powered by AI — Construction Value Engineering Platform</div>
        <div>Generated on ${now} | Powered by Gemini 2.0 Flash + Hybrid RAG Engine</div>
        <div style="margin-top:4px;">© Ninetynine Inc. | ninetynine99.co.kr</div>
      </div>`;

      preview.innerHTML = html;
      printBtn.style.display = 'block';

    } catch (e) {
      preview.innerHTML = '<div style="padding:40px;text-align:center;color:#EF4444;">보고서 생성 오류: ' + e.message + '</div>';
    } finally {
      genBtn.disabled = false;
      genBtn.textContent = '📄 보고서 생성';
    }
  });

  // ── PDF 내보내기 (브라우저 인쇄) ──
  printBtn.addEventListener('click', () => {
    const content = preview.innerHTML;
    const win = window.open('', '_blank');
    win.document.write(`<!DOCTYPE html><html><head><meta charset="UTF-8"><title>VE 보고서</title>
      <style>
        body{margin:0;padding:0;font-family:'Pretendard','Noto Sans KR',sans-serif;-webkit-print-color-adjust:exact;print-color-adjust:exact;}
        @page{margin:15mm;}
        @media print{body{font-size:11px;}}
      </style></head><body>${content}</body></html>`);
    win.document.close();
    setTimeout(() => { win.print(); }, 500);
  });

  // ── 유틸 ──
  function escHtml(str) {
    return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function formatContent(text) {
    let html = escHtml(text);
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\n/g, '<br>');
    return html;
  }

  function countAgents(messages) {
    return new Set(messages.map(m => m.agent_id)).size;
  }
})();
