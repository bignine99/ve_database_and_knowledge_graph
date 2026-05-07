const COLORS = {
  navy:'#061E4A',accent:'#3B82F6',emerald:'#10B981',orange:'#F97316',red:'#EF4444',neutral:'#64748B',
  palette:['#061E4A','#3B82F6','#64748B','#94A3B8','#475569','#1E293B','#CBD5E1','#334155','#0F172A','#E2E8F0'],
};
const NODE_COLORS={Project:'#061E4A',Alternative:'#3B82F6',WorkType:'#475569',SubWorkType:'#64748B',Space:'#94A3B8',Material:'#CBD5E1',ValueType:'#1E293B',Location:'#334155',PerformanceCategory:'#E2E8F0'};
const NODE_KR={Project:'프로젝트',Alternative:'대안',WorkType:'공사(HOW1)',SubWorkType:'대공종(HOW2)',Space:'공간',Material:'자재',ValueType:'가치유형',Location:'위치',PerformanceCategory:'성능항목'};
const PAGE_TITLES={overview:'종합 현황',alternatives:'VE 대안 목록',cost:'비용 분석',kg:'지식 그래프',ai:'AI VE 자문',performance:'성능 분석',veagent:'VE Multiple Agents',report:'VE 보고서 생성',lcc:'LCC 비교 분석',fast:'FAST Diagram',compare:'프로젝트 비교',eval:'아이디어 평가',ebook:'VE E-book'};
let charts={},allAlternatives=[],kgData=null,kgNetwork=null;

// Navigation
document.querySelectorAll('.nav-item').forEach(item=>{
  item.addEventListener('click',e=>{
    // 외부 링크(target=_blank)는 브라우저 기본 동작 허용
    if(item.getAttribute('target')==='_blank') return;
    e.preventDefault();
    const page=item.dataset.page;
    if(!page) return;
    document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
    item.classList.add('active');
    document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
    const pageEl=document.getElementById(`page-${page}`);
    if(pageEl) pageEl.classList.add('active');
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
  // ML Cluster Insights
  loadClusterInsights();
}
async function loadClusterInsights(){
  try {
    const res=await fetch('/api/clusters');const d=await res.json();
    if(d.error||!d.clusters)return;
    const el=document.getElementById('cluster-cards');
    const clrPal=['#061E4A','#3B82F6','#10B981','#F97316','#EF4444','#64748B','#8B5CF6','#EC4899'];
    el.innerHTML=d.clusters.map((c,i)=>{
      const h2=c.how2_distribution.map(h=>`<span style="font-size:9px;background:#F1F5F9;padding:1px 5px;border-radius:2px;">${h.name.replace('공사','')} ${h.count}</span>`).join(' ');
      const savColor=c.avg_savings_rate>0?COLORS.emerald:c.avg_savings_rate<0?COLORS.red:COLORS.neutral;
      const valColor=c.avg_value_change>0?COLORS.emerald:COLORS.neutral;
      return `<div style="background:#fff;border:1px solid var(--color-border);border-radius:4px;padding:14px;border-left:3px solid ${clrPal[i%8]};">
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
          <span style="font-family:Outfit;font-weight:700;font-size:16px;color:${clrPal[i%8]};">${c.size}</span>
          <span style="font-size:11px;font-weight:600;color:var(--color-navy);flex:1;">${c.label}</span>
        </div>
        <div style="font-size:10px;color:var(--color-text-secondary);margin-bottom:6px;">
          대표: #${String(c.representative.alt_number).padStart(3,'0')} ${c.representative.title.substring(0,30)}
        </div>
        <div style="display:flex;gap:12px;margin-bottom:6px;">
          <span style="font-family:Outfit;font-size:11px;color:${savColor};">절감 ${c.avg_savings_rate>0?'+':''}${c.avg_savings_rate}%</span>
          <span style="font-family:Outfit;font-size:11px;color:${valColor};">가치 ${c.avg_value_change>0?'+':''}${c.avg_value_change.toFixed(1)}%</span>
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:3px;">${h2}</div>
      </div>`;
    }).join('');
  } catch(e){/* cluster load fail silent */}
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
    ${d.ai_descriptions&&d.ai_descriptions.length>0?`<div class="detail-section" style="margin-top:14px;"><h4>AI 이미지 서술 (Gemini 2.0 Flash)</h4>${d.ai_descriptions.map(ai=>`<p style="margin-bottom:6px;font-size:12px;"><strong>${ai.image_type==='original'?'원안':'대안'}:</strong> ${(ai.description||'').substring(0,300)}</p>`).join('')}</div>`:''}
    <div class="detail-section" style="margin-top:14px;" id="similar-section"><h4>유사 대안 (Embedding 기반)</h4><p style="font-size:11px;color:var(--color-text-muted);">로딩 중...</p></div>`;
  document.getElementById('detail-modal').classList.add('active');
  // 유사 대안 비동기 로드
  try {
    const simRes=await fetch(`/api/alternatives/${n}/similar?top_k=5`);
    const simData=await simRes.json();
    const simEl=document.getElementById('similar-section');
    if(simData.similar&&simData.similar.length>0){
      simEl.innerHTML=`<h4>유사 대안 (Embedding 기반)</h4>
        <div style="display:flex;flex-direction:column;gap:6px;">${simData.similar.map(s=>{
          const simPct=(s.similarity*100).toFixed(1);
          const barColor=s.similarity>0.7?COLORS.emerald:s.similarity>0.5?COLORS.accent:COLORS.neutral;
          return `<div style="display:flex;align-items:center;gap:8px;padding:6px 8px;background:var(--bg-secondary);border-radius:3px;cursor:pointer;font-size:11px;" onclick="showDetail(${s.alt_number})">
            <span style="font-family:Outfit;font-weight:600;color:var(--color-navy);min-width:35px;">${String(s.alt_number).padStart(3,'0')}</span>
            <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${(s.title||'').substring(0,40)}</span>
            <div style="width:60px;height:3px;background:#E2E8F0;border-radius:2px;overflow:hidden;"><div style="width:${Math.round(s.similarity*100)}%;height:100%;background:${barColor};border-radius:2px;"></div></div>
            <span style="font-family:Outfit;font-size:10px;color:var(--color-text-muted);min-width:32px;">${simPct}%</span>
            <span class="badge badge-blue" style="font-size:9px;padding:1px 4px;">${s.value_type||''}</span>
          </div>`;}).join('')}</div>`;
    } else {
      simEl.innerHTML=`<h4>유사 대안</h4><p style="font-size:11px;color:var(--color-text-muted);">유사 대안 데이터가 없습니다.</p>`;
    }
  } catch(e){ /* 유사 대안 로드 실패 시 무시 */ }
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

// ═══ PAGE 5: AI VE 자문 (Hybrid RAG) ═══
document.getElementById('ai-search-btn').addEventListener('click',async()=>{
  const q=document.getElementById('ai-query').value.trim();if(!q)return;
  const mode=document.getElementById('ai-mode').value;
  const useGemini=document.getElementById('ai-gemini-toggle').checked;
  const el=document.getElementById('ai-response');
  const geminiEl=document.getElementById('ai-gemini-answer');
  const timeEl=document.getElementById('ai-search-time');

  el.innerHTML='<p style="text-align:center;color:var(--color-text-muted);padding:30px;">'+
    (mode==='kg'?'지식 그래프 검색 중...':'Hybrid RAG 검색 중 (Embedding + KG)...')+'</p>';
  geminiEl.style.display='none';
  timeEl.textContent='';

  const t0=performance.now();

  try {
    let data;
    if(mode==='kg'){
      // Legacy KG-only mode
      const res=await fetch(`/api/kg/query?q=${encodeURIComponent(q)}`);
      data=await res.json();
      data._mode='kg';
    } else if(mode==='semantic'){
      const res=await fetch(`/api/search?q=${encodeURIComponent(q)}&top_k=10`);
      data=await res.json();
      data._mode='semantic';
    } else {
      // Hybrid (default)
      const res=await fetch(`/api/ai/search?q=${encodeURIComponent(q)}&top_k=10&gemini=${useGemini}`);
      data=await res.json();
      data._mode='hybrid';
    }

    const elapsed=((performance.now()-t0)/1000).toFixed(2);
    timeEl.textContent=`${elapsed}s`;

    if(data.error){
      el.innerHTML=`<p style="color:${COLORS.red};padding:20px;">${data.error}</p>`;
      return;
    }

    // Gemini 답변 표시
    if(data.gemini_answer && data.gemini_answer.length>10){
      geminiEl.style.display='block';
      geminiEl.innerHTML=`<div style="font-size:11px;font-weight:600;color:var(--color-navy);margin-bottom:8px;">
        Gemini AI 분석 답변</div><div style="white-space:pre-wrap;">${data.gemini_answer.replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>').replace(/\n/g,'<br>')}</div>`;
    }

    // 결과 렌더링
    const alts=data.alternatives||[];
    const count=data.combined_count||data.matched_count||data.count||alts.length;
    if(count===0){
      el.innerHTML='<p style="color:var(--color-text-muted);padding:20px;">매칭되는 대안이 없습니다. 다른 질의어를 시도해 보세요.</p>';
      return;
    }

    // 모드별 메타 정보
    let metaHtml=`<div style="margin-bottom:12px;font-size:11px;color:var(--color-text-secondary);">
      <strong>질의:</strong> ${data.query}<br>`;
    if(data._mode==='hybrid'){
      metaHtml+=`<strong>엔진:</strong> Hybrid RAG | <strong>시맨틱:</strong> ${data.semantic_count||0}건 | <strong>KG:</strong> ${data.kg_match_count||0}건 | <strong>결과:</strong> ${count}건`;
      if(data.query_spaces&&data.query_spaces.length) metaHtml+=` | <strong>공간:</strong> ${data.query_spaces.join(', ')}`;
      if(data.query_how2&&data.query_how2.length) metaHtml+=` | <strong>대공종:</strong> ${data.query_how2.map(h=>h[1]).join(', ')}`;
    } else if(data._mode==='semantic'){
      metaHtml+=`<strong>엔진:</strong> Embedding Only | <strong>결과:</strong> ${count}건`;
    } else {
      metaHtml+=`<strong>엔진:</strong> KG Hop (Legacy) | <strong>결과:</strong> ${count}건`;
      if(data.query_spaces&&data.query_spaces.length) metaHtml+=` | <strong>공간:</strong> ${data.query_spaces.join(', ')}`;
      if(data.query_how2&&data.query_how2.length) metaHtml+=` | <strong>대공종:</strong> ${data.query_how2.map(h=>h[1]).join(', ')}`;
    }
    metaHtml+=`</div>`;

    // 대안 카드 렌더링
    el.innerHTML=metaHtml + alts.map(a=>{
      const num=a.alt_number||parseInt((a.label||'').replace('대안-',''),10)||0;
      const title=a.title||(a.label?a.label:'');

      // 유사도/점수 바
      let scoreHtml='';
      if(data._mode==='hybrid' || data._mode==='semantic'){
        const sim=a.final_score||a.similarity||0;
        const pct=Math.round(sim*100);
        const barColor=sim>0.7?COLORS.emerald:sim>0.4?COLORS.accent:COLORS.neutral;
        scoreHtml=`<div style="display:flex;align-items:center;gap:6px;margin-top:6px;">
          <div style="flex:1;height:4px;background:#E2E8F0;border-radius:2px;overflow:hidden;">
            <div style="width:${pct}%;height:100%;background:${barColor};border-radius:2px;"></div>
          </div>
          <span style="font-family:Outfit;font-size:10px;color:var(--color-text-muted);min-width:35px;">${(sim*100).toFixed(1)}%</span>`;
        if(a.semantic_score!==undefined && a.kg_score!==undefined){
          scoreHtml+=`<span style="font-size:9px;color:var(--color-text-muted);">S:${(a.semantic_score*100).toFixed(0)} K:${a.kg_score}</span>`;
        }
        scoreHtml+=`</div>`;
      }

      // KG 경로
      const paths=a.kg_paths||a.paths||[];
      const pathHtml=paths.length?`<div class="path">${paths.join(' | ')}</div>`:'';

      // 메타 정보
      const metaParts=[];
      if(a.value_type) metaParts.push(`가치: ${a.value_type}`);
      if(a.savings) metaParts.push(`절감: ${Math.round(a.savings)}백만원`);
      if(a.value_change) metaParts.push(`가치변화: ${a.value_change>0?'+':''}${a.value_change}%`);
      if(a.how2_name) metaParts.push(a.how2_name);
      if(a.space) metaParts.push(a.space);

      return `<div class="result-card" onclick="showDetail(${num})">
        <h5>${num?String(num).padStart(3,'0')+'번 — ':''}${(title||'').substring(0,55)}</h5>
        ${scoreHtml}
        ${pathHtml}
        <div class="meta">${metaParts.join(' | ')}</div>
      </div>`;
    }).join('');

    // Hybrid 시각화 (semantic + kg 결합)
    if(data._mode!=='semantic') visualizeAIHops(data);

  } catch(err) {
    el.innerHTML=`<p style="color:${COLORS.red};padding:20px;">검색 오류: ${err.message}</p>`;
  }
});
document.getElementById('ai-query').addEventListener('keypress',e=>{if(e.key==='Enter')document.getElementById('ai-search-btn').click();});

function visualizeAIHops(data){
  const nodes=[],edges=[],ns=new Set();
  nodes.push({id:'q',label:'질의',group:'Project',size:20});ns.add('q');
  if(data.query_spaces)data.query_spaces.forEach(sp=>{const id=`sp_${sp}`;if(!ns.has(id)){nodes.push({id,label:sp,group:'Space'});ns.add(id);}edges.push({from:'q',to:id,label:'공간'});});
  if(data.query_how2)data.query_how2.forEach(h=>{const id=`h2_${h[0]}`;if(!ns.has(id)){nodes.push({id,label:h[1],group:'SubWorkType'});ns.add(id);}edges.push({from:'q',to:id,label:'대공종'});});
  const alts=data.alternatives||[];
  alts.forEach(a=>{const aid=a.alt_id||a.label||`alt_${a.alt_number}`;if(!ns.has(aid)){nodes.push({id:aid,label:a.alt_number?`대안-${String(a.alt_number).padStart(2,'0')}`:a.label,group:'Alternative',title:a.title});ns.add(aid);}
    const paths=a.kg_paths||a.paths||[];
    paths.forEach(p=>{const m=p.match(/→\[(.+?)\]→ (.+)/);if(m){const tid=`t_${m[2]}`;const g=m[1].includes('LOCATED')?'Space':'SubWorkType';if(!ns.has(tid)){nodes.push({id:tid,label:m[2],group:g});ns.add(tid);}edges.push({from:aid,to:tid,label:m[1].replace(/_/g,' ')});}});
    // 시맨틱 매칭만인 경우 질의에서 직접 연결
    if(paths.length===0 && (a.similarity||a.semantic_score)){edges.push({from:'q',to:aid,label:`sim ${((a.similarity||a.semantic_score)*100).toFixed(0)}%`,dashes:true,color:{color:'#3B82F644'}});}
  });
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
