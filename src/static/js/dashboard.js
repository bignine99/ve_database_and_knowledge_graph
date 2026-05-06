const COLORS = {
  navy:'#061E4A',accent:'#3B82F6',emerald:'#10B981',orange:'#F97316',red:'#EF4444',neutral:'#64748B',
  palette:['#061E4A','#3B82F6','#64748B','#94A3B8','#475569','#1E293B','#CBD5E1','#334155','#0F172A','#E2E8F0'],
};
const NODE_COLORS={Project:'#061E4A',Alternative:'#3B82F6',WorkType:'#475569',SubWorkType:'#64748B',Space:'#94A3B8',Material:'#CBD5E1',ValueType:'#1E293B',Location:'#334155',PerformanceCategory:'#E2E8F0'};
const NODE_KR={Project:'프로젝트',Alternative:'대안',WorkType:'공사(HOW1)',SubWorkType:'대공종(HOW2)',Space:'공간',Material:'자재',ValueType:'가치유형',Location:'위치',PerformanceCategory:'성능항목'};
const PAGE_TITLES={overview:'종합 현황',alternatives:'VE 대안 목록',cost:'비용 분석',kg:'지식 그래프',ai:'AI VE 자문',performance:'성능 분석'};
let charts={},allAlternatives=[],kgData=null,kgNetwork=null;

// Navigation
document.querySelectorAll('.nav-item').forEach(item=>{
  item.addEventListener('click',e=>{
    e.preventDefault();
    const page=item.dataset.page;
    document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
    item.classList.add('active');
    document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
    document.getElementById(`page-${page}`).classList.add('active');
    document.getElementById('page-title').textContent=PAGE_TITLES[page]||page;
    if(page==='kg')loadKG();
    if(page==='alternatives')loadAlternatives();
    if(page==='cost')loadCostData();
    if(page==='performance')loadPerformance();
  });
});

// Modal
document.getElementById('modal-close-btn').addEventListener('click',()=>document.getElementById('detail-modal').classList.remove('active'));
document.getElementById('detail-modal').addEventListener('click',e=>{if(e.target===e.currentTarget)e.currentTarget.classList.remove('active');});

// KG Sidebar
document.getElementById('kg-sidebar-close').addEventListener('click',()=>document.getElementById('kg-sidebar').classList.remove('open'));

// ═══ PAGE 1: 종합 현황 ═══
async function loadOverview(){
  const res=await fetch('/api/stats');const data=await res.json();
  document.getElementById('kpi-row').innerHTML=`
    <div class="kpi-card"><div class="kpi-label">TOTAL VE ALTERNATIVES</div><div class="kpi-value">${data.total_alternatives}</div><div class="kpi-sub">CUBE Classification 100%</div></div>
    <div class="kpi-card"><div class="kpi-label">AVG. SAVINGS RATE</div><div class="kpi-value">${data.avg_savings_rate}%</div><div class="kpi-sub">Lifecycle Cost Basis</div></div>
    <div class="kpi-card"><div class="kpi-label">AI COVERAGE</div><div class="kpi-value">${data.ai_coverage}%</div><div class="kpi-sub">Gemini 2.0 Flash</div></div>
    <div class="kpi-card"><div class="kpi-label">VALUE INNOVATION</div><div class="kpi-value">${data.value_innovation_rate}%</div><div class="kpi-sub">KG: ${data.kg_nodes} Nodes, ${data.kg_edges} Edges</div></div>`;
  // HOW1
  if(charts.how1)charts.how1.destroy();
  charts.how1=new Chart(document.getElementById('chart-how1'),{type:'doughnut',data:{labels:Object.keys(data.how1_distribution),datasets:[{data:Object.values(data.how1_distribution),backgroundColor:COLORS.palette.slice(0,6),borderWidth:0}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'right',labels:{font:{size:11,family:'Pretendard'},padding:10}}}}});
  // ValueType
  const vt=data.vtype_distribution;
  if(charts.vtype)charts.vtype.destroy();
  charts.vtype=new Chart(document.getElementById('chart-vtype'),{type:'doughnut',data:{labels:vt.map(d=>d.type),datasets:[{data:vt.map(d=>d.count),backgroundColor:['#061E4A','#3B82F6','#64748B','#94A3B8'],borderWidth:0}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'right',labels:{font:{size:11,family:'Pretendard'},padding:10}}}}});
  // HOW2
  const h2=data.how2_distribution.slice(0,15);
  if(charts.how2)charts.how2.destroy();
  charts.how2=new Chart(document.getElementById('chart-how2'),{type:'bar',data:{labels:h2.map(d=>d.name.replace('공사','')),datasets:[{data:h2.map(d=>d.count),backgroundColor:COLORS.accent+'CC',borderRadius:3}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{color:'#F1F5F9'},ticks:{font:{size:10,family:'Outfit'}}},y:{grid:{display:false},ticks:{font:{size:10,family:'Pretendard'}}}}}});
  // Savings
  const altRes=await fetch('/api/alternatives');const altData=await altRes.json();
  const sv=altData.filter(a=>a.savings!==0).sort((a,b)=>b.savings-a.savings).slice(0,20);
  if(charts.savings)charts.savings.destroy();
  charts.savings=new Chart(document.getElementById('chart-savings'),{type:'bar',data:{labels:sv.map(d=>`${d.alt_number}번`),datasets:[{data:sv.map(d=>d.savings),backgroundColor:sv.map(d=>d.savings>0?COLORS.emerald+'CC':COLORS.red+'CC'),borderRadius:3}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{grid:{display:false},ticks:{font:{size:9,family:'Outfit'}}},y:{grid:{color:'#F1F5F9'},ticks:{font:{size:10,family:'Outfit'},callback:v=>v+'백만'}}}}});
  // Extended charts
  loadExtendedOverview();
}
async function loadExtendedOverview(){
  const res=await fetch('/api/stats/extended');const d=await res.json();
  const CO={responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}}};
  // Project dist
  if(charts.proj)charts.proj.destroy();
  charts.proj=new Chart(document.getElementById('chart-proj'),{type:'bar',data:{labels:d.project_distribution.map(r=>r.name.substring(0,15)),datasets:[{data:d.project_distribution.map(r=>r.count),backgroundColor:COLORS.palette.slice(0,3),borderRadius:4}]},options:{...CO,scales:{x:{ticks:{font:{size:9,family:'Pretendard'}}},y:{ticks:{font:{size:10,family:'Outfit'}}}}}});
  // Field dist
  if(charts.field)charts.field.destroy();
  charts.field=new Chart(document.getElementById('chart-field'),{type:'doughnut',data:{labels:d.field_distribution.map(r=>r.field),datasets:[{data:d.field_distribution.map(r=>r.count),backgroundColor:['#061E4A','#3B82F6','#64748B','#94A3B8'],borderWidth:0}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'right',labels:{font:{size:11,family:'Pretendard'}}}}}});
  // Space dist
  if(charts.space)charts.space.destroy();
  charts.space=new Chart(document.getElementById('chart-space'),{type:'bar',data:{labels:d.space_distribution.map(r=>r.space),datasets:[{data:d.space_distribution.map(r=>r.count),backgroundColor:'#3B82F688',borderRadius:2}]},options:{indexAxis:'y',...CO,scales:{x:{ticks:{font:{size:10,family:'Outfit'}}},y:{ticks:{font:{size:10,family:'Pretendard'}}}}}});
  // Value Top 10
  if(charts.valueTop)charts.valueTop.destroy();
  charts.valueTop=new Chart(document.getElementById('chart-value-top'),{type:'bar',data:{labels:d.value_top10.map(r=>`#${r.num}`),datasets:[{label:'Value Change(%)',data:d.value_top10.map(r=>r.value),backgroundColor:'#061E4A99',borderRadius:2}]},options:{indexAxis:'y',...CO,scales:{x:{ticks:{font:{size:10,family:'Outfit'},callback:v=>v+'%'}},y:{ticks:{font:{size:10,family:'Outfit'}}}}}});
}

// ═══ PAGE 2: VE 대안 목록 ═══
async function loadAlternatives(){
  const s=document.getElementById('alt-search').value,h=document.getElementById('alt-how1-filter').value,v=document.getElementById('alt-vtype-filter').value;
  const res=await fetch(`/api/alternatives?q=${encodeURIComponent(s)}&how1=${h}&vtype=${encodeURIComponent(v)}`);
  allAlternatives=await res.json();renderAlternatives(allAlternatives);
}
function renderAlternatives(data){
  document.getElementById('alt-count').textContent=`${data.length}개 대안`;
  document.getElementById('alt-tbody').innerHTML=data.map(a=>`
    <tr onclick="showDetail(${a.alt_number})">
      <td style="font-family:Outfit;font-weight:600;color:var(--color-navy);">${String(a.alt_number).padStart(3,'0')}</td>
      <td>${a.title?(a.title.substring(0,50)+(a.title.length>50?'...':'')):''}></td>
      <td><span class="badge badge-blue">${a.how2_code||''}</span></td>
      <td style="font-size:11px;color:var(--color-text-secondary);">${a.space||'-'}</td>
      <td><span class="badge ${getBadge(a.value_type)}">${a.value_type||'-'}</span></td>
      <td style="font-family:Outfit;color:${a.cost_change>0?COLORS.red:COLORS.emerald};">${a.cost_change>0?'+':''}${a.cost_change}%</td>
      <td style="font-family:Outfit;color:${a.value_change>=0?COLORS.emerald:COLORS.red};">${a.value_change>=0?'+':''}${a.value_change}%</td>
    </tr>`).join('');
}
function getBadge(v){return v==='가치혁신형'?'badge-blue':v==='성능강조형'?'badge-green':v==='비용절감형'?'badge-orange':v==='성능향상형'?'badge-navy':'badge-blue';}
['alt-search','alt-how1-filter','alt-vtype-filter'].forEach(id=>{const el=document.getElementById(id);el.addEventListener('input',loadAlternatives);el.addEventListener('change',loadAlternatives);});

// ═══ DETAIL MODAL (이미지 + 효과) ═══
async function showDetail(n){
  const res=await fetch(`/api/alternatives/${n}`);const d=await res.json();
  const perfColor=c=>c>=0?COLORS.emerald:COLORS.red;
  const costColor=c=>c>0?COLORS.red:COLORS.emerald;

  // 이미지 섹션
  let imgHtml='';
  if(d.images&&d.images.length>0){
    const origImg=d.images.find(i=>i.type==='original_diagram'||i.type==='original');
    const altImg=d.images.find(i=>i.type==='alternative_diagram'||i.type==='alternative');
    imgHtml=`<div class="detail-images">
      <div class="detail-img-card"><h4>원안 (기존 설계)</h4>${origImg?`<img src="/api/serve_abs_image?path=${encodeURIComponent(origImg.path)}" alt="원안">`:'<div class="no-img">이미지 없음</div>'}</div>
      <div class="detail-img-card"><h4>대안 (변경 설계)</h4>${altImg?`<img src="/api/serve_abs_image?path=${encodeURIComponent(altImg.path)}" alt="대안">`:'<div class="no-img">이미지 없음</div>'}</div>
    </div>`;
  }

  // 효과 요약 카드
  const effectHtml=`<div class="effect-summary">
    <div class="effect-item"><div class="effect-label">성능 변화</div><div class="effect-value" style="color:${perfColor(d.perf_change)}">${d.perf_change>=0?'+':''}${d.perf_change}%</div><div class="effect-sub">성능 평가 기준</div></div>
    <div class="effect-item"><div class="effect-label">비용 변화</div><div class="effect-value" style="color:${costColor(d.cost_change)}">${d.cost_change>0?'+':''}${d.cost_change}%</div><div class="effect-sub">생애주기비용 기준</div></div>
    <div class="effect-item"><div class="effect-label">가치 변화</div><div class="effect-value" style="color:${perfColor(d.value_change)}">${d.value_change>=0?'+':''}${d.value_change}%</div><div class="effect-sub">V = P + C 종합</div></div>
  </div>`;

  document.getElementById('modal-title').textContent=`${String(n).padStart(3,'0')}번 — ${d.title}`;
  document.getElementById('modal-body').innerHTML=`
    <div style="display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap;">
      <span class="badge badge-blue">${d.how2_code} ${d.how2_name}</span>
      <span class="badge ${getBadge(d.value_type)}">${d.value_type}</span>
      ${d.space?`<span class="badge badge-navy">${d.space}</span>`:''}
      ${d.location?`<span class="badge badge-green">${d.location}</span>`:''}
    </div>
    ${imgHtml}
    ${effectHtml}
    <div class="detail-grid">
      <div class="detail-section"><h4>원안 (기존 설계)</h4><p>${d.original_desc||'-'}</p></div>
      <div class="detail-section"><h4>대안 (변경 설계)</h4><p>${d.alternative_desc||'-'}</p></div>
    </div>
    ${d.analysis_summary?`<div class="detail-section" style="margin-bottom:14px;"><h4>분석 요약</h4><p>${d.analysis_summary}</p></div>`:''}
    <div class="detail-grid">
      <div class="detail-section"><h4>비용 평가</h4><table class="data-table" style="font-size:11px;">
        ${d.costs.map(c=>`<tr><td>${c.type==='project_initial'?'초기투자비':c.type==='project_lifecycle'?'생애주기비용':'유지관리비'}</td><td style="font-family:Outfit;">${fmt(c.savings)}백만원</td><td style="font-family:Outfit;color:var(--color-accent);">${c.rate||0}%</td></tr>`).join('')}
      </table></div>
      <div class="detail-section"><h4>성능 평가</h4><table class="data-table" style="font-size:11px;">
        ${d.performances.slice(0,6).map(p=>`<tr><td>${p.category}</td><td style="font-family:Outfit;">${p.original||0}</td><td style="font-family:Outfit;">${p.alternative||0}</td><td style="font-family:Outfit;color:${(p.delta||0)>=0?COLORS.emerald:COLORS.red};">${(p.delta||0)>=0?'+':''}${p.delta||0}</td></tr>`).join('')}
      </table></div>
    </div>
    ${d.ai_descriptions&&d.ai_descriptions.length>0?`<div class="detail-section" style="margin-top:14px;"><h4>AI 이미지 서술 (Gemini 2.0 Flash)</h4>${d.ai_descriptions.map(ai=>`<p style="margin-bottom:6px;font-size:12px;"><strong>${ai.image_type==='original'?'원안':'대안'}:</strong> ${(ai.description||'').substring(0,300)}</p>`).join('')}</div>`:''}`;
  document.getElementById('detail-modal').classList.add('active');
}
window.showDetail=showDetail;
function fmt(n){return n?Number(n).toLocaleString('ko-KR',{maximumFractionDigits:2}):'-';}

// ═══ PAGE 3: 비용 분석 ═══
async function loadCostData(){
  const res=await fetch('/api/alternatives');const data=await res.json();
  const wc=data.filter(a=>a.savings!==0).sort((a,b)=>b.savings-a.savings);
  if(charts.costBar)charts.costBar.destroy();
  charts.costBar=new Chart(document.getElementById('chart-cost-bar'),{type:'bar',data:{labels:wc.map(d=>`${d.alt_number}`),datasets:[{label:'Savings(M)',data:wc.map(d=>d.savings),backgroundColor:wc.map(d=>d.savings>0?'#3B82F688':'#94A3B888'),borderRadius:2}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{ticks:{font:{size:8,family:'Outfit'}}},y:{ticks:{font:{size:10,family:'Outfit'}}}}}});
  if(charts.costScatter)charts.costScatter.destroy();
  charts.costScatter=new Chart(document.getElementById('chart-cost-scatter'),{type:'scatter',data:{datasets:[{data:data.filter(a=>a.savings_rate!==0).map(a=>({x:a.savings_rate,y:a.value_change})),backgroundColor:COLORS.accent+'88',borderColor:COLORS.accent,borderWidth:1,pointRadius:5}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{title:{display:true,text:'절감율(%)',font:{size:10}},ticks:{font:{size:10,family:'Outfit'}}},y:{title:{display:true,text:'가치변화(%)',font:{size:10}},ticks:{font:{size:10,family:'Outfit'}}}}}});
  document.getElementById('cost-tbody').innerHTML=wc.map(a=>`<tr onclick="showDetail(${a.alt_number})"><td style="font-family:Outfit;font-weight:600;">${a.alt_number}</td><td>${a.title?(a.title.substring(0,45)):''}</td><td style="font-family:Outfit;">-</td><td style="font-family:Outfit;">-</td><td style="font-family:Outfit;font-weight:600;color:${a.savings>0?'#061E4A':'#94A3B8'};">${fmt(a.savings)}</td><td style="font-family:Outfit;color:#3B82F6;">${a.savings_rate}%</td></tr>`).join('');
  // Extended cost charts
  const ext=await fetch('/api/stats/extended');const ed=await ext.json();
  if(charts.savHist)charts.savHist.destroy();
  charts.savHist=new Chart(document.getElementById('chart-savings-hist'),{type:'bar',data:{labels:ed.savings_histogram.map(r=>r.range),datasets:[{data:ed.savings_histogram.map(r=>r.count),backgroundColor:'#061E4ACC',borderRadius:2}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{ticks:{font:{size:10,family:'Pretendard'}}},y:{ticks:{font:{size:10,family:'Outfit'}}}}}});
  if(charts.how2Sav)charts.how2Sav.destroy();
  charts.how2Sav=new Chart(document.getElementById('chart-how2-savings'),{type:'bar',data:{labels:ed.how2_avg_savings.map(r=>r.name),datasets:[{label:'Avg. Savings(%)',data:ed.how2_avg_savings.map(r=>r.rate),backgroundColor:'#3B82F688',borderRadius:2}]},options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{ticks:{font:{size:10,family:'Outfit'},callback:v=>v+'%'}},y:{ticks:{font:{size:9,family:'Pretendard'}}}}}});
}

// ═══ PAGE 4: 지식 그래프 + 노드 클릭 사이드패널 ═══
async function loadKG(){
  const res=await fetch('/api/kg/data');kgData=await res.json();
  document.getElementById('kg-node-count').textContent=`노드: ${kgData.nodes.length}`;
  document.getElementById('kg-edge-count').textContent=`엣지: ${kgData.edges.length}`;
  renderKG(kgData.nodes,kgData.edges);
}
function renderKG(nodes,edges){
  const container=document.getElementById('kg-container');
  const options={
    nodes:{shape:'dot',size:12,font:{size:10,face:'Pretendard',color:'#1E293B'},borderWidth:1.5},
    edges:{width:0.8,color:{color:'#CBD5E1',highlight:'#3B82F6'},font:{size:7,face:'Outfit',color:'#94A3B8'},arrows:{to:{scaleFactor:0.5}}},
    physics:{barnesHut:{gravitationalConstant:-3000,centralGravity:0.2,springLength:120},stabilization:{iterations:200}},
    interaction:{hover:true,tooltipDelay:100},
    groups:{
      Project:{color:{background:'#FF6B6B',border:'#E05252'},size:22},
      Alternative:{color:{background:'#4ECDC4',border:'#38B2AC'},size:8},
      WorkType:{color:{background:'#96CEB4',border:'#7AB89E'},size:16},
      SubWorkType:{color:{background:'#2ECC71',border:'#27AE60'},size:14},
      Space:{color:{background:'#87CEEB',border:'#6BB5D4'},size:13},
      Material:{color:{background:'#FFEAA7',border:'#E6D190'},size:10},
      ValueType:{color:{background:'#F39C12',border:'#D68910'},size:15},
      Location:{color:{background:'#45B7D1',border:'#3A9DB5'},size:12},
      PerformanceCategory:{color:{background:'#DDA0DD',border:'#C48BC4'},size:11},
    },
  };
  kgNetwork=new vis.Network(container,{nodes,edges},options);
  kgNetwork.on('click',function(params){
    if(params.nodes.length>0)showKGNodeInfo(params.nodes[0]);
  });
}

function showKGNodeInfo(nodeId){
  const node=kgData.nodes.find(n=>n.id===nodeId);
  if(!node)return;
  const sidebar=document.getElementById('kg-sidebar');
  const body=document.getElementById('kg-sidebar-body');
  sidebar.classList.add('open');

  // 연결된 엣지/노드 수집
  const connected=[];
  kgData.edges.forEach(e=>{
    if(e.from===nodeId){const t=kgData.nodes.find(n=>n.id===e.to);if(t)connected.push({node:t,edge:e.label,dir:'out'});}
    if(e.to===nodeId){const t=kgData.nodes.find(n=>n.id===e.from);if(t)connected.push({node:t,edge:e.label,dir:'in'});}
  });

  // 대안 노드면 상세보기 버튼 추가
  const isAlt=node.group==='Alternative';
  const altNum=isAlt?parseInt(node.label.replace('대안-',''),10):0;

  body.innerHTML=`
    <div style="margin-bottom:12px;">
      <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px;">
        <span class="legend-dot" style="background:${NODE_COLORS[node.group]||'#ccc'};width:10px;height:10px;"></span>
        <span style="font-size:11px;color:var(--color-text-muted);">${NODE_KR[node.group]||node.group}</span>
      </div>
      <div style="font-size:14px;font-weight:600;color:var(--color-navy);margin-bottom:4px;">${node.label}</div>
      ${node.title?`<div style="font-size:11px;color:var(--color-text-secondary);line-height:1.5;">${node.title}</div>`:''}
    </div>
    ${isAlt?`<button onclick="showDetail(${altNum})" style="width:100%;padding:8px;background:var(--color-accent);color:#fff;border:none;border-radius:3px;font-family:Pretendard;font-size:12px;font-weight:600;cursor:pointer;margin-bottom:12px;">상세 정보 보기 (이미지/효과)</button>`:''}
    <div class="kg-info-row"><span class="kg-info-label">노드 유형</span><span class="kg-info-value">${NODE_KR[node.group]||node.group}</span></div>
    <div class="kg-info-row"><span class="kg-info-label">연결 수</span><span class="kg-info-value">${connected.length}개</span></div>
    <div class="kg-info-row"><span class="kg-info-label">노드 ID</span><span class="kg-info-value" style="font-size:9px;">${nodeId.substring(0,30)}</span></div>
    <div class="kg-connected-list">
      <div style="font-size:11px;font-weight:600;color:var(--color-navy);margin-bottom:6px;">연결된 노드 (${connected.length}개)</div>
      ${connected.slice(0,30).map(c=>`
        <div class="kg-connected-item" onclick="kgNetwork.selectNodes(['${c.node.id}']);showKGNodeInfo('${c.node.id}');">
          <span class="kg-connected-dot" style="background:${NODE_COLORS[c.node.group]||'#ccc'};"></span>
          <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${c.node.label}</span>
          <span style="color:var(--color-accent);font-size:9px;">${c.edge}</span>
        </div>`).join('')}
      ${connected.length>30?`<div style="text-align:center;color:var(--color-text-muted);font-size:10px;padding:4px;">... 외 ${connected.length-30}개</div>`:''}
    </div>`;
}

document.getElementById('kg-filter').addEventListener('change',function(){
  if(!kgData)return;
  const filter=this.value;
  if(!filter){renderKG(kgData.nodes,kgData.edges);return;}
  const nodeIds=new Set(kgData.nodes.filter(n=>n.group===filter||n.group==='Project').map(n=>n.id));
  kgData.edges.forEach(e=>{if(nodeIds.has(e.to))nodeIds.add(e.from);if(nodeIds.has(e.from))nodeIds.add(e.to);});
  renderKG(kgData.nodes.filter(n=>nodeIds.has(n.id)),kgData.edges.filter(e=>nodeIds.has(e.from)&&nodeIds.has(e.to)));
});

// ═══ PAGE 5: AI VE 자문 ═══
document.getElementById('ai-search-btn').addEventListener('click',async()=>{
  const q=document.getElementById('ai-query').value.trim();if(!q)return;
  const el=document.getElementById('ai-response');
  el.innerHTML='<p style="text-align:center;color:var(--color-text-muted);padding:30px;">지식 그래프 검색 중...</p>';
  const res=await fetch(`/api/kg/query?q=${encodeURIComponent(q)}`);const data=await res.json();
  if(data.matched_count===0){el.innerHTML='<p style="color:var(--color-text-muted);padding:20px;">매칭되는 대안이 없습니다. 다른 질의어를 시도해 보세요.</p>';return;}
  el.innerHTML=`
    <div style="margin-bottom:12px;font-size:11px;color:var(--color-text-secondary);">
      <strong>질의:</strong> ${data.query}<br>
      <strong>공간:</strong> ${data.query_spaces.join(', ')||'-'} |
      <strong>대공종:</strong> ${data.query_how2.map(h=>h[1]).join(', ')||'-'} |
      <strong>결과:</strong> ${data.matched_count}개 대안
    </div>
    ${data.alternatives.map(a=>{const num=parseInt(a.label.replace('대안-',''),10);return`
      <div class="result-card" onclick="showDetail(${num})">
        <h5>${a.label} — ${a.title?(a.title.substring(0,55)):''}</h5>
        <div class="path">${a.paths.join(' | ')}</div>
        <div class="meta">
          가치유형: ${a.value_type||'-'} | 절감액: ${a.savings}백만원 | 가치변화: ${a.value_change}%
          ${a.materials.length>0?' | 자재: '+a.materials.map(m=>m.name).join(', '):''}
        </div>
      </div>`;}).join('')}`;
  visualizeAIHops(data);
});
document.getElementById('ai-query').addEventListener('keypress',e=>{if(e.key==='Enter')document.getElementById('ai-search-btn').click();});

function visualizeAIHops(data){
  const nodes=[],edges=[],ns=new Set();
  nodes.push({id:'q',label:'질의',group:'Project',size:20});ns.add('q');
  data.query_spaces.forEach(sp=>{const id=`sp_${sp}`;if(!ns.has(id)){nodes.push({id,label:sp,group:'Space'});ns.add(id);}edges.push({from:'q',to:id,label:'공간'});});
  data.query_how2.forEach(h=>{const id=`h2_${h[0]}`;if(!ns.has(id)){nodes.push({id,label:h[1],group:'SubWorkType'});ns.add(id);}edges.push({from:'q',to:id,label:'대공종'});});
  data.alternatives.forEach(a=>{const aid=a.alt_id||a.label;if(!ns.has(aid)){nodes.push({id:aid,label:a.label,group:'Alternative',title:a.title});ns.add(aid);}
    a.paths.forEach(p=>{const m=p.match(/→\[(.+?)\]→ (.+)/);if(m){const tid=`t_${m[2]}`;const g=m[1].includes('LOCATED')?'Space':'SubWorkType';if(!ns.has(tid)){nodes.push({id:tid,label:m[2],group:g});ns.add(tid);}edges.push({from:aid,to:tid,label:m[1].replace(/_/g,' ')});}});});
  new vis.Network(document.getElementById('ai-kg-container'),{nodes,edges},{
    nodes:{shape:'dot',size:12,font:{size:10,face:'Pretendard'}},
    edges:{width:1,color:'#CBD5E1',font:{size:8,face:'Outfit',color:'#94A3B8'},arrows:{to:{scaleFactor:0.5}}},
    physics:{barnesHut:{gravitationalConstant:-2000,springLength:100}},
    groups:{Project:{color:{background:'#061E4A'},size:22},Alternative:{color:{background:'#3B82F6'},size:14},SubWorkType:{color:{background:'#64748B'},size:16},Space:{color:{background:'#94A3B8'},size:16},Material:{color:{background:'#CBD5E1'},size:12}},
  });
}

// ═══ PAGE 6: 성능 분석 ═══
async function loadPerformance(){
  const res=await fetch('/api/stats/extended');const d=await res.json();
  const pc=d.perf_categories;
  // KPI
  document.getElementById('perf-kpi-row').innerHTML=pc.map(c=>`<div class="kpi-card"><div class="kpi-label">${c.category}</div><div class="kpi-value">${c.delta>=0?'+':''}${c.delta}</div><div class="kpi-sub">${c.count} Evaluations</div></div>`).join('');
  // Radar
  if(charts.perfRadar)charts.perfRadar.destroy();
  charts.perfRadar=new Chart(document.getElementById('chart-perf-radar'),{type:'radar',data:{labels:pc.map(c=>c.category),datasets:[{label:'Original',data:pc.map(c=>c.original),borderColor:'#94A3B8',backgroundColor:'#94A3B811',borderWidth:2,pointRadius:3},{label:'Alternative',data:pc.map(c=>c.alternative),borderColor:'#061E4A',backgroundColor:'#061E4A11',borderWidth:2,pointRadius:3}]},options:{responsive:true,maintainAspectRatio:false,scales:{r:{beginAtZero:true,grid:{color:'#F1F5F9'},ticks:{font:{size:9,family:'Outfit'}}}},plugins:{legend:{position:'bottom',labels:{font:{size:11,family:'Outfit'}}}}}});
  // Quadrant scatter
  const vtColors={'가치혁신형':'#061E4A','성능강조형':'#3B82F6','비용절감형':'#64748B','성능향상형':'#94A3B8'};
  const datasets={};
  d.quadrant_data.forEach(q=>{const vt=q.vtype||'기타';if(!datasets[vt])datasets[vt]={label:vt,data:[],backgroundColor:(vtColors[vt]||'#CBD5E1')+'77',borderColor:vtColors[vt]||'#CBD5E1',borderWidth:1,pointRadius:4};datasets[vt].data.push({x:q.cost,y:q.perf});});
  if(charts.quadrant)charts.quadrant.destroy();
  charts.quadrant=new Chart(document.getElementById('chart-quadrant'),{type:'scatter',data:{datasets:Object.values(datasets)},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'bottom',labels:{font:{size:10,family:'Pretendard'}}}},scales:{x:{title:{display:true,text:'Cost Change(%)',font:{size:10,family:'Outfit'}},grid:{color:'#F1F5F9'}},y:{title:{display:true,text:'Performance Change(%)',font:{size:10,family:'Outfit'}},grid:{color:'#F1F5F9'}}}}});
  // Perf compare bar
  if(charts.perfComp)charts.perfComp.destroy();
  charts.perfComp=new Chart(document.getElementById('chart-perf-compare'),{type:'bar',data:{labels:pc.map(c=>c.category),datasets:[{label:'Original',data:pc.map(c=>c.original),backgroundColor:'#94A3B877',borderRadius:2},{label:'Alternative',data:pc.map(c=>c.alternative),backgroundColor:'#061E4A99',borderRadius:2}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'bottom',labels:{font:{size:10,family:'Outfit'}}}},scales:{x:{ticks:{font:{size:10,family:'Pretendard'}}},y:{ticks:{font:{size:10,family:'Outfit'}}}}}});
  // Heatmap as bubble
  const hLabels=['건축','토목','조경','전기','기계설비','소방'];
  const vLabels=['가치혁신형','성능강조형','비용절감형','성능향상형'];
  const bubbles=d.heatmap.map(h=>({x:hLabels.indexOf(h.how1),y:vLabels.indexOf(h.vtype),r:Math.sqrt(h.count)*4,count:h.count}));
  if(charts.heatmap)charts.heatmap.destroy();
  charts.heatmap=new Chart(document.getElementById('chart-heatmap'),{type:'bubble',data:{datasets:[{data:bubbles,backgroundColor:'#061E4A44',borderColor:'#061E4A',borderWidth:1}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{callbacks:{label:ctx=>`${hLabels[ctx.raw.x]} / ${vLabels[ctx.raw.y]}: ${ctx.raw.count}`}}},scales:{x:{type:'linear',min:-0.5,max:5.5,ticks:{callback:v=>hLabels[v]||'',font:{size:10,family:'Pretendard'}}},y:{type:'linear',min:-0.5,max:3.5,ticks:{callback:v=>vLabels[v]||'',font:{size:10,family:'Pretendard'}}}}}});
}

loadOverview();
