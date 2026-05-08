/**
 * VE Roundtable — Multi-Agent 토론 채팅 UI (Async v2)
 *
 * 비동기 처리:
 * 1. POST /api/ve/roundtable → 세션 ID 즉시 반환
 * 2. GET /api/ve/roundtable/<id>/messages?since=<n> → 1초 폴링
 * 3. 새 메시지 도착 시 타이핑 애니메이션으로 순차 표시
 */
(function () {
  const startBtn = document.getElementById('rt-start-btn');
  if (!startBtn) return;

  const uploadZone = document.getElementById('rt-upload-zone');
  const fileInput = document.getElementById('rt-file-input');
  const fileNameEl = document.getElementById('rt-file-name');
  const chatArea = document.getElementById('rt-chat-area');
  const statusBadge = document.getElementById('rt-status-badge');
  const elapsedEl = document.getElementById('rt-elapsed');
  const roomTitle = document.getElementById('rt-room-title');
  const agentsDisplay = document.getElementById('rt-agents-display');

  let uploadedFile = null;

  // ── 참여자 드롭다운 ──
  const dropdownBtn = document.getElementById('rt-agent-dropdown-btn');
  const dropdownList = document.getElementById('rt-agent-dropdown-list');
  const agentSummary = document.getElementById('rt-agent-summary');
  const agentCheckboxes = document.querySelectorAll('.rt-agent-cb');

  if (dropdownBtn && dropdownList) {
    dropdownBtn.addEventListener('click', () => {
      const isOpen = dropdownList.style.display !== 'none';
      dropdownList.style.display = isOpen ? 'none' : 'block';
      dropdownBtn.style.borderColor = isOpen ? '' : '#3b82f6';
    });

    // 외부 클릭 닫기
    document.addEventListener('click', (e) => {
      const wrapper = document.getElementById('rt-agent-dropdown-wrapper');
      if (wrapper && !wrapper.contains(e.target)) {
        dropdownList.style.display = 'none';
        dropdownBtn.style.borderColor = '';
      }
    });

    // 체크 변경 시 요약 업데이트 + #rt-disciplines 동기화
    function updateAgentSummary() {
      const checked = document.querySelectorAll('.rt-agent-cb:checked');
      const count = checked.length + 1; // +1 for VE Leader (always)
      agentSummary.textContent = count + '명 선택됨';

      // 기존 #rt-disciplines 동기화 (ve-agent.js의 disciplines 수집 호환)
      const discDiv = document.getElementById('rt-disciplines');
      discDiv.innerHTML = '';
      checked.forEach(cb => {
        const hidden = document.createElement('input');
        hidden.type = 'checkbox';
        hidden.value = cb.value;
        hidden.checked = true;
        discDiv.appendChild(hidden);
      });
    }

    agentCheckboxes.forEach(cb => cb.addEventListener('change', updateAgentSummary));
    updateAgentSummary(); // 초기화
  }


  // ── 파일 업로드 ──
  uploadZone.addEventListener('click', () => fileInput.click());
  uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.style.borderColor = '#3b82f6'; });
  uploadZone.addEventListener('dragleave', () => { uploadZone.style.borderColor = ''; });
  uploadZone.addEventListener('drop', e => {
    e.preventDefault();
    uploadZone.style.borderColor = '';
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
  });
  fileInput.addEventListener('change', () => { if (fileInput.files.length) handleFile(fileInput.files[0]); });

  function handleFile(file) {
    const ext = file.name.split('.').pop().toLowerCase();
    if (!['pdf', 'txt'].includes(ext)) { alert('PDF 또는 TXT 파일만 지원합니다.'); return; }
    uploadedFile = file;
    fileNameEl.style.display = 'block';
    fileNameEl.textContent = '\uD83D\uDCC4 ' + file.name + ' (' + (file.size / 1024).toFixed(1) + 'KB)';
    uploadZone.style.borderColor = '#3b82f6';
  }

  // ── VE 회의 시작 ──
  startBtn.addEventListener('click', async () => {
    const projectText = document.getElementById('rt-project-text').value.trim();
    const projectName = document.getElementById('rt-project-name').value.trim();

    if (!uploadedFile && !projectText) {
      alert('\uD504\uB85C\uC81D\uD2B8 \uD30C\uC77C\uC744 \uC5C5\uB85C\uB4DC\uD558\uAC70\uB098 \uC124\uBA85\uC744 \uC785\uB825\uD558\uC138\uC694.');
      return;
    }

    // 관심 분야 수집
    const disciplines = [];
    document.querySelectorAll('#rt-disciplines input:checked').forEach(cb => disciplines.push(cb.value));

    // UI 상태 변경
    startBtn.disabled = true;
    startBtn.textContent = '\uD68C\uC758 \uC900\uBE44 \uC911...';
    startBtn.style.opacity = '0.6';
    statusBadge.textContent = '\uC900\uBE44 \uC911';
    statusBadge.style.background = '#fef3c7';
    statusBadge.style.color = '#92400e';
    chatArea.innerHTML = '';
    agentsDisplay.innerHTML = '';

    // 시스템 메시지
    addSystemMsg('\uD68C\uC758\uB97C \uC900\uBE44\uD558\uACE0 \uC788\uC2B5\uB2C8\uB2E4. AI \uC804\uBB38\uAC00\uB4E4\uC744 \uCD08\uCCAD\uD558\uB294 \uC911...');

    const t0 = performance.now();

    try {
      // Step 1: 세션 생성 (즉시 반환)
      let res;
      if (uploadedFile) {
        const formData = new FormData();
        formData.append('file', uploadedFile);
        formData.append('project_name', projectName || uploadedFile.name);
        formData.append('disciplines', disciplines.join(','));
        res = await fetch('/api/ve/roundtable', { method: 'POST', body: formData });
      } else {
        res = await fetch('/api/ve/roundtable', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ project_text: projectText, project_name: projectName || 'VE \uD504\uB85C\uC81D\uD2B8', disciplines }),
        });
      }

      if (!res.ok) { const err = await res.json(); throw new Error(err.error || '\uC11C\uBC84 \uC624\uB958'); }
      const data = await res.json();
      const sessionId = data.session_id;

      if (projectName) roomTitle.textContent = projectName;

      // UI 상태: 토론 중
      statusBadge.textContent = '\uD1A0\uB860 \uC911';
      statusBadge.style.background = '#dbeafe';
      statusBadge.style.color = '#1e40af';
      startBtn.textContent = '\uD68C\uC758 \uC9C4\uD589 \uC911...';
      addSystemMsg('\uD68C\uC758\uAC00 \uC2DC\uC791\uB418\uC5C8\uC2B5\uB2C8\uB2E4. AI \uC804\uBB38\uAC00\uB4E4\uC774 \uC21C\uCC28\uC801\uC73C\uB85C \uBC1C\uC5B8\uD569\uB2C8\uB2E4...');

      // Step 2: 폴링으로 메시지 수신
      let since = 0;
      const seenAgents = new Set();
      const POLL_INTERVAL = 1200;  // 1.2초
      const MAX_POLLS = 120;       // 최대 144초 (120 × 1.2초)

      // 타이핑 중 표시 (로딩 인디케이터)
      const typingIndicator = createTypingIndicator();
      chatArea.appendChild(typingIndicator);

      for (let poll = 0; poll < MAX_POLLS; poll++) {
        await sleep(POLL_INTERVAL);

        const msgRes = await fetch(`/api/ve/roundtable/${sessionId}/messages?since=${since}`);
        if (!msgRes.ok) {
           throw new Error('서버와의 연결이 끊어졌거나 세션을 찾을 수 없습니다.');
        }
        const msgData = await msgRes.json();

        // 새 메시지 처리
        if (msgData.new_messages && msgData.new_messages.length > 0) {
          // 타이핑 인디케이터 제거 후 메시지 표시
          typingIndicator.remove();

          for (const msg of msgData.new_messages) {
            // Agent 목록 업데이트
            if (!seenAgents.has(msg.agent_id)) {
              seenAgents.add(msg.agent_id);
              agentsDisplay.innerHTML += '<div style="display:flex;align-items:center;gap:6px;padding:4px 0;">' +
                '<span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;background:' + msg.agent_color + '15;border-radius:50%;font-size:12px;">' + msg.agent_emoji + '</span>' +
                '<span style="font-size:10px;color:' + msg.agent_color + ';font-weight:600;">' + msg.agent_name + '</span>' +
                '</div>';
            }

            // 메시지 렌더링 (타이핑 애니메이션)
            await renderMessage(msg, 200);
          }
          since = msgData.total_count;

          // 진행 중이면 타이핑 인디케이터 다시 추가
          if (msgData.status === 'running') {
            const newIndicator = createTypingIndicator();
            chatArea.appendChild(newIndicator);
            // 새 indicator를 참조하도록 교체 (다음 루프에서 제거)
            Object.assign(typingIndicator, { remove: () => newIndicator.remove() });
          }
        }

        // 경과 시간 업데이트
        const elapsed = ((performance.now() - t0) / 1000).toFixed(1);
        elapsedEl.textContent = elapsed + '\uCD08';

        // 완료/실패 체크
        if (msgData.status === 'completed' || msgData.status === 'failed') {
          typingIndicator.remove();
          if (msgData.status === 'completed') {
            statusBadge.textContent = '\uC644\uB8CC';
            statusBadge.style.background = '#dcfce7';
            statusBadge.style.color = '#166534';
            addSystemMsg('\uD68C\uC758\uAC00 \uC644\uB8CC\uB418\uC5C8\uC2B5\uB2C8\uB2E4. (' + elapsed + '\uCD08)');
          } else {
            statusBadge.textContent = '\uC624\uB958';
            statusBadge.style.background = '#fee2e2';
            statusBadge.style.color = '#991b1b';
            addSystemMsg('\u274C \uD68C\uC758 \uC911 \uC624\uB958\uAC00 \uBC1C\uC0DD\uD588\uC2B5\uB2C8\uB2E4: ' + (msgData.error || ''));
          }
          break;
        }
      }

      // If loop finished (timeout or break without completion), clean up indicator
      if (typingIndicator && typingIndicator.parentNode) {
          typingIndicator.remove();
      }

    } catch (e) {
      if (typeof typingIndicator !== 'undefined' && typingIndicator.parentNode) {
          typingIndicator.remove();
      }
      addSystemMsg('\u274C \uC624\uB958: ' + e.message);
      statusBadge.textContent = '\uC624\uB958';
      statusBadge.style.background = '#fee2e2';
      statusBadge.style.color = '#991b1b';
    } finally {
      startBtn.disabled = false;
      startBtn.textContent = '\uD83C\uDF99 VE \uD68C\uC758 \uC2DC\uC791';
      startBtn.style.opacity = '1';
    }
  });

  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  function createTypingIndicator() {
    const div = document.createElement('div');
    div.className = 'rt-typing-indicator';
    div.style.cssText = 'display:flex;gap:4px;padding:16px 20px;align-items:center;';
    div.innerHTML =
      '<div style="display:flex;gap:4px;">' +
        '<span class="rt-dot" style="width:6px;height:6px;border-radius:50%;background:#94a3b8;animation:rtBounce 1.4s ease-in-out infinite;"></span>' +
        '<span class="rt-dot" style="width:6px;height:6px;border-radius:50%;background:#94a3b8;animation:rtBounce 1.4s ease-in-out infinite 0.2s;"></span>' +
        '<span class="rt-dot" style="width:6px;height:6px;border-radius:50%;background:#94a3b8;animation:rtBounce 1.4s ease-in-out infinite 0.4s;"></span>' +
      '</div>' +
      '<span style="font-size:10px;color:#94a3b8;margin-left:8px;">AI \uC804\uBB38\uAC00 \uBD84\uC11D \uC911...</span>';

    // 바운스 애니메이션 CSS 삽입 (최초 1회)
    if (!document.getElementById('rt-bounce-style')) {
      const style = document.createElement('style');
      style.id = 'rt-bounce-style';
      style.textContent = '@keyframes rtBounce{0%,80%,100%{transform:translateY(0)}40%{transform:translateY(-8px)}}';
      document.head.appendChild(style);
    }

    return div;
  }

  function addSystemMsg(text) {
    const div = document.createElement('div');
    div.style.cssText = 'text-align:center;font-size:10px;color:var(--color-text-muted);padding:8px;background:var(--bg-secondary);border-radius:12px;';
    div.textContent = text;
    chatArea.appendChild(div);
  }

  function renderMessage(msg, delay) {
    return new Promise(resolve => {
      setTimeout(() => {
        const wrapper = document.createElement('div');
        wrapper.style.cssText = 'display:flex;gap:10px;align-items:flex-start;opacity:0;transform:translateY(10px);transition:all 0.4s ease;';

        const isSummary = msg.msg_type === 'summary';

        // 아바타
        const avatar = document.createElement('div');
        avatar.style.cssText = 'min-width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px;background:' + msg.agent_color + '15;border:2px solid ' + msg.agent_color + '30;';
        avatar.textContent = msg.agent_emoji;

        // 메시지 본문
        const body = document.createElement('div');
        body.style.cssText = 'flex:1;min-width:0;';

        // 이름 + 역할
        const header = document.createElement('div');
        header.style.cssText = 'display:flex;align-items:center;gap:6px;margin-bottom:4px;';
        header.innerHTML = '<span style="font-size:12px;font-weight:700;color:' + msg.agent_color + ';">' + msg.agent_name + '</span>' +
          '<span style="font-size:9px;color:var(--color-text-muted);">Step ' + msg.step + '</span>';

        // 내용
        const content = document.createElement('div');
        const bgColor = isSummary ? '#fffbeb' : '#f8fafc';
        const borderColor = isSummary ? '#fcd34d' : msg.agent_color + '20';
        content.style.cssText = 'font-size:12px;line-height:1.7;color:var(--color-text-primary);background:' + bgColor + ';border:1px solid ' + borderColor + ';border-radius:0 12px 12px 12px;padding:12px 14px;white-space:pre-wrap;word-break:break-word;';

        if (isSummary) {
          content.innerHTML = '<div style="font-size:10px;font-weight:700;color:#92400e;margin-bottom:6px;">\uD83D\uDCCB \uD68C\uC758 \uC885\uD569</div>' + formatText(msg.content);
        } else {
          content.innerHTML = formatText(msg.content);
        }

        body.appendChild(header);
        body.appendChild(content);
        wrapper.appendChild(avatar);
        wrapper.appendChild(body);
        chatArea.appendChild(wrapper);

        // 애니메이션
        requestAnimationFrame(() => {
          wrapper.style.opacity = '1';
          wrapper.style.transform = 'translateY(0)';
        });

        // 스크롤
        chatArea.scrollTop = chatArea.scrollHeight;
        resolve();
      }, delay);
    });
  }

  function formatText(text) {
    // **bold** → <strong>
    let html = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // 줄바꿈
    html = html.replace(/\n/g, '<br>');
    return html;
  }
})();
