const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
function icon(name) {
  const paths = {
    chart: '<path d="M4 17l5-5 4 3 7-9M14 6h6v6"/>',
    grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    history: '<path d="M3 10a9 9 0 1 1 2 8M3 4v6h6M12 7v5l3 2"/>',
    settings: '<path d="M4 6h16M4 12h16M4 18h16"/><circle cx="9" cy="6" r="2" fill="var(--surface)"/><circle cx="15" cy="12" r="2" fill="var(--surface)"/><circle cx="8" cy="18" r="2" fill="var(--surface)"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    download: '<path d="M12 3v12m-4-4 4 4 4-4M4 16v4h16v-4"/>',
    sparkles: '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5ZM20 2v4m-2-2h4"/>'
  };
  return `<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">${paths[name] || paths.chart}</svg>`;
}
$$('[data-icon]').forEach(el => { el.innerHTML = icon(el.dataset.icon); });
let bootstrap, current, jobs = [], activeTab = 'market', period = '1M', view = 'research';
let polling = false;
const statuses = {queued:'대기 중',running:'분석 중',cancelling:'중지 요청됨',completed:'분석 완료',failed:'실행 실패',cancelled:'중지됨',interrupted:'서버 중단',imported:'가져온 보고서'};
const labels = {market:'시장 분석',fundamentals:'펀더멘털',news:'뉴스',sentiment:'시장 심리'};
const fields = {market:'market_report',fundamentals:'fundamentals_report',news:'news_report',sentiment:'sentiment_report'};
const stages = ['전문가 분석','리서치 토론','트레이더 전략','리스크 검토','최종 판단'];
const active = job => job && ['queued','running','cancelling'].includes(job.status);
const text = (selector, value) => { $(selector).textContent = value ?? '—'; };
function element(tag, value, className) { const el=document.createElement(tag);if(value!==undefined)el.textContent=value;if(className)el.className=className;return el; }
function reportBody(content) {
  const root=element('div',undefined,'report-body');
  function inline(target,value){value.split(/(\*\*[^*]+\*\*)/g).forEach(part=>target.append(part.startsWith('**')&&part.endsWith('**')?element('strong',part.slice(2,-2)):document.createTextNode(part)));}
  const lines=String(content).split('\n');
  for(let i=0;i<lines.length;i++){
    const line=lines[i];
    if(!line.trim())continue;
    if(/^\|/.test(line)&&/^\|[\s:|\-]+\|\s*$/.test(lines[i+1]||'')){
      const wrap=element('div',undefined,'table-scroll'),table=element('table');wrap.append(table);
      const cells=value=>value.replace(/^\||\|$/g,'').split('|');
      const head=element('tr');cells(line).forEach(c=>{const th=element('th');inline(th,c.trim());head.append(th);});table.append(head);i++;
      while(/^\|/.test(lines[i+1]||'')){const row=element('tr');cells(lines[++i]).forEach(c=>{const td=element('td');inline(td,c.trim());row.append(td);});table.append(row);}root.append(wrap);continue;
    }
    const heading=line.match(/^(#{1,6})\s+(.*)/);
    if(heading){const h=element('h'+Math.min(heading[1].length+2,6));inline(h,heading[2]);root.append(h);continue;}
    if(/^---+$/.test(line.trim())){root.append(element('hr'));continue;}
    const p=element(line.startsWith('>')?'blockquote':'p');inline(p,line.replace(/^>\s?/,''));root.append(p);
  }
  return root;
}
function toast(message) { text('#toast',message);$('#toast').classList.add('show');setTimeout(()=>$('#toast').classList.remove('show'),5000); }
async function api(path, data) {
  const response=await fetch(path,{headers:data?{'Content-Type':'application/json','X-Workspace-Token':bootstrap.token}:{},method:data?'POST':'GET',body:data?JSON.stringify(data):undefined});
  const result=await response.json(); if(!response.ok)throw new Error(result.error||'서버 요청에 실패했습니다.');return result;
}
function showView(next) {
  view=next;
  ['research','history','settings'].forEach(v=>$('#'+v+'View').hidden=v!==next||(v==='research'&&!current));
  $('#emptyView').hidden=next!=='research'||!!current;
  const titles={research:'리서치 스튜디오',history:'분석 기록',settings:'모델 및 설정'};
  text('#pageTitle',titles[next]);text('#breadcrumb',titles[next]);
  $$('.nav').forEach(b=>{b.classList.toggle('active',b.dataset.view===next);b.setAttribute('aria-current',b.dataset.view===next?'page':'false');});
}
function renderHistory() {
  $('#recent').replaceChildren();$('#historyList').replaceChildren();
  if(!jobs.length)$('#historyList').append(element('p','아직 저장된 분석이 없습니다. 새 분석을 시작하세요.','muted'));
  jobs.forEach((job,index)=>{
    const cfg=job.config;
    const make=(cls)=>{const b=element('button',undefined,cls);b.append(element('span',cfg.symbol[0],'recent-icon'));const content=element('div',cfg.symbol);content.append(element('small',`${cfg.date} · ${statuses[job.status]||job.status}`));b.append(content);b.onclick=()=>openJob(job.id);return b;};
    if(index<5)$('#recent').append(make('recent-button'));
    const row=make('history-row');row.append(element('span',job.source?'Alpha-Ledger':cfg.provider),element('span','보고서 보기 →'));$('#historyList').append(row);
  });text('#historyCount',jobs.length);
  $('#newAnalysis').disabled=jobs.some(active);
}
async function openJob(id) {try{current=await api('/api/jobs/'+id);render();showView('research');}catch(e){toast(e.message);} }
function renderChart() {
  const data=current.reports.market_data||{};
  text('#marketSource',data.source||'미제공');
  const all=data.bars||[];const count={'1W':5,'1M':22,'3M':66}[period];const bars=all.slice(-count);
  $('#chart').replaceChildren();$('#chartLabels').replaceChildren();
  text('#lastBar',all.at(-1)?.date);text('#volume',all.at(-1)?.volume?.toLocaleString());text('#currency',data.currency||'—');
  if(!bars.length){text('#price','—');text('#priceChange','가격 데이터 없음');text('.price-row small',current.source?'가져온 원문에는 별도 가격 시계열이 없습니다.':'가격 데이터 수집 전이거나 제공자에서 데이터를 반환하지 않았습니다.');return;}
  text('#price',bars.at(-1).close.toLocaleString(undefined,{maximumFractionDigits:2}));
  const delta=bars.at(-1).close-bars[0].close;const pct=bars[0].close?delta/bars[0].close*100:0;
  text('#priceChange',`${delta>=0?'↑':'↓'} ${delta.toFixed(2)} (${pct.toFixed(2)}%)`);
  $('#priceChange').classList.toggle('negative',delta<0);
  text('.price-row small',`${data.source} · ${bars[0].date} ~ ${bars.at(-1).date} · ${data.currency||'통화 정보 없음'}`);
  const lo=Math.min(...bars.map(b=>b.close)),hi=Math.max(...bars.map(b=>b.close)),span=hi-lo||1;
  const points=bars.map((b,i)=>[i*680/Math.max(bars.length-1,1),160-(b.close-lo)/span*140]);
  const line=points.map((p,i)=>(i?'L':'M')+p.join(',')).join(' ');
  // Geometry consists solely of finite numbers from the price-data API.
  $('#chart').innerHTML=`<path d="${line} L680,185 L0,185 Z" fill="var(--green-soft)"/><path d="${line}" fill="none" stroke="var(--chart-line)" stroke-width="2"/>`;
  [bars[0].date,bars[Math.floor(bars.length/2)].date,bars.at(-1).date].forEach(d=>$('#chartLabels').append(element('span',d)));
}
function renderReport() {
  $$('[data-tab]').forEach(b=>{b.classList.toggle('active',b.dataset.tab===activeTab);b.setAttribute('aria-selected',b.dataset.tab===activeTab);b.disabled=!current.config.analysts.includes(b.dataset.tab);});
  const root=$('#reportContent');root.replaceChildren();
  root.append(element('h4',labels[activeTab]));
  root.append(reportBody(current.reports[fields[activeTab]]||'아직 생성된 보고서가 없습니다. 완료된 단계부터 표시됩니다.'));
}
function render() {
  if(!current)return;
  const cfg=current.config,r=current.reports;
  text('#stockName',cfg.symbol);text('#ticker','');text('#stockLogo',cfg.symbol[0]);
  text('#stockMeta',`${cfg.provider} · 기준일 ${cfg.date}`);text('#analysisDate',cfg.date);
  text('#runStatus',statuses[current.status]);text('#sourceLabel',current.source?'외부 보고서':'웹 분석');
  $('#sourceLink').hidden=!current.source;
  if(current.source&&/^https:\/\/github\.com\//.test(current.source))$('#sourceLink').href=current.source;
  const notice=current.error||(current.status==='cancelling'?'현재 모델 호출이 끝나는 다음 단계에서 중지됩니다.':current.source?'Alpha-Ledger에 기록된 AI 분석 원문입니다. 보고서의 주장은 별도로 검증하지 않았으며 현재 시세를 의미하지 않습니다.':'');
  $('#jobNotice').hidden=!notice;text('#jobNotice',notice);
  $('#cancelRun').hidden=!active(current);$('#cancelRun').disabled=current.status==='cancelling';
  $('#retryRun').hidden=active(current)||!!current.source;
  $('#pipeline').replaceChildren();
  stages.forEach((name,i)=>{const done=current.stage>i;const step=element('div',undefined,'step '+(active(current)&&current.stage===i?'running':done?'':'wait'));step.append(element('span',done?'✓':String(i+1),'step-number'),element('strong',name));$('#pipeline').append(step);});
  renderChart();if(!cfg.analysts.includes(activeTab))activeTab=cfg.analysts[0]||'market';renderReport();
  text('.report-card .muted',cfg.analysts.length+'명의 분석가');
  text('.debate-card .sample',current.source?'가져온 원문':`최대 ${cfg.depth} 라운드`);
  text('.debate-grid > div:first-child h4','상승 관점');text('.debate-grid > div:last-child h4','하락 관점');
  text('.debate-grid > div:first-child p',r.investment_debate_state?.bull_history||'아직 생성된 의견이 없습니다.');
  text('.debate-grid > div:last-child p',r.investment_debate_state?.bear_history||'아직 생성된 의견이 없습니다.');
  text('.debate-card details p',r.investment_plan||'아직 종합 의견이 없습니다.');
  text('.decision-rating',current.signal||'—');
  $('.decision-rating').classList.toggle('negative',['Sell','Underweight'].includes(current.signal));
  text('.decision-card > p',r.final_trade_decision?'최종 판단의 근거를 아래에서 확인하세요.':'리스크 검토와 최종 판단을 기다리고 있습니다.');
  text('#decisionProvider',cfg.provider);text('#decisionStatus',statuses[current.status]);
  const order=['Sell','Underweight','Hold','Overweight','Buy'];$$('.rating-scale i').forEach((el,i)=>el.classList.toggle('on',order.indexOf(current.signal)===i));
  $('#download').disabled=!Object.values(r).some(Boolean);
  $('#activity').replaceChildren();
  current.events.slice(-6).forEach(e=>{const row=element('div',undefined,'activity-item');row.append(element('span','✓','activity-check'));const info=element('div');info.append(element('strong',stages[e.stage]||'보고서'),element('small',new Date(e.time).toLocaleTimeString()));row.append(info);$('#activity').append(row);});
  if(!current.events.length)$('#activity').append(element('p',current.source?'원본 보고서에서 가져왔습니다.':'분석 엔진을 준비하고 있습니다.','muted'));
  text('#activitySummary',statuses[current.status]);
  const elapsed=current.started?Math.floor((new Date(current.finished||Date.now())-new Date(current.started))/1000):null;
  text('#elapsed',elapsed===null?'—':`${Math.floor(elapsed/60)}분 ${elapsed%60}초`);
  $('#detailReports').replaceChildren();
  const sections=[['트레이더 전략',r.trader_investment_plan],['리스크 검토',r.risk_debate_state?.history||[r.risk_debate_state?.aggressive_history,r.risk_debate_state?.conservative_history,r.risk_debate_state?.neutral_history].filter(Boolean).join('\n\n')],['최종 판단 전문',r.final_trade_decision],['원본 통합 보고서',r.original_report]];
  sections.forEach(([label,value])=>{if(!value)return;const details=element('details');details.append(element('summary',label),reportBody(value));$('#detailReports').append(details);});
}
function providerOptions(select) {select.replaceChildren();bootstrap.providers.forEach(p=>{const o=element('option',p.label);o.value=p.id;select.append(o);});}
function modelOptions(provider,quick,deep) {
  const p=bootstrap.providers.find(x=>x.id===provider);if(!p)return;
  [['quick',quick],['deep',deep]].forEach(([mode,input])=>{const list=$('#'+mode+'Options');list.replaceChildren();p[mode].filter(([,id])=>id!=='custom').forEach(([label,id])=>{const o=element('option',label);o.value=id;list.append(o);});input.value=p[mode].find(([,id])=>id!=='custom')?.[1]||'';});
}
function setPreferences(p) {$('#provider').value=p.provider;$('#settingsProvider').value=p.provider;modelOptions(p.provider,$('#runQuick'),$('#runDeep'));$('#quickModel').value=p.quickModel;$('#deepModel').value=p.deepModel;$('#runQuick').value=p.quickModel;$('#runDeep').value=p.deepModel;providerStatus();}
function providerStatus() {const p=bootstrap.providers.find(x=>x.id===$('#settingsProvider').value);text('#providerStatus',p.configured===false?`설정 필요: ${p.key_env||'Codex CLI 설치 및 로그인'}`:p.id==='codex'?'Codex CLI 감지됨 · 구독 로그인 여부는 실행 시 확인합니다.':p.configured?'서버 인증 환경변수가 설정되어 있습니다.':'서버의 제공자 인증 또는 로컬 엔드포인트를 사용합니다.');}
function formConfig() {return {symbol:$('#symbol').value.trim(),date:$('#date').value,provider:$('#provider').value,quickModel:$('#runQuick').value.trim(),deepModel:$('#runDeep').value.trim(),depth:Number($('#depth').value),analysts:$$('input[name="analyst"]:checked').map(x=>x.value)};}
async function refresh() {
  if(polling||!bootstrap)return;polling=true;
  try {jobs=await api('/api/jobs');renderHistory();if(current){const record=jobs.find(j=>j.id===current.id);if(record&&(record.updated!==current.updated||active(current))){current=await api('/api/jobs/'+current.id);render();}}text('#connectionMessage','');$('#connectionMessage').hidden=true;}
  catch(e){$('#connectionMessage').hidden=false;text('#connectionMessage','서버 연결이 끊겼습니다. 다시 연결을 시도합니다. 기록은 서버에 저장되어 있습니다.');}
  finally{polling=false;}
}
$$('.nav').forEach(b=>b.onclick=()=>showView(b.dataset.view));
$$('[data-tab]').forEach(b=>b.onclick=()=>{activeTab=b.dataset.tab;renderReport();});
$$('[data-period]').forEach(b=>b.onclick=()=>{period=b.dataset.period;$$('[data-period]').forEach(x=>{x.classList.toggle('selected',x===b);x.setAttribute('aria-pressed',x===b);});renderChart();});
$('#newAnalysis').onclick=()=>{if(!bootstrap)return;$('#formError').textContent='';$('#analysisDialog').showModal();};
$('#closeDialog').onclick=()=>$('#analysisDialog').close();
$('#provider').onchange=()=>modelOptions($('#provider').value,$('#runQuick'),$('#runDeep'));
$('#symbol').oninput=()=>{const crypto=/-(USD[TC]?|BTC|ETH)$/.test($('#symbol').value.trim().toUpperCase());const control=$('input[name="analyst"][value="fundamentals"]');control.disabled=crypto;if(crypto)control.checked=false;};
$('#settingsProvider').onchange=()=>{modelOptions($('#settingsProvider').value,$('#quickModel'),$('#deepModel'));providerStatus();};
$('#saveSettings').onclick=async()=>{try{const config={...formConfig(),symbol:'SPY',date:bootstrap.today,analysts:['market'],provider:$('#settingsProvider').value,quickModel:$('#quickModel').value,deepModel:$('#deepModel').value};await api('/api/preferences',config);setPreferences(config);toast('기본 모델 설정을 저장했습니다.');}catch(e){toast(e.message);}};
$('#analysisForm').onsubmit=async e=>{e.preventDefault();const submit=$('#analysisForm button[type="submit"]');submit.disabled=true;try{current=await api('/api/jobs',formConfig());$('#analysisDialog').close();render();showView('research');await refresh();}catch(error){text('#formError',error.message);}finally{submit.disabled=false;}};
$('#cancelRun').onclick=async()=>{try{current=await api(`/api/jobs/${current.id}/cancel`,{});render();}catch(e){toast(e.message);}};
$('#retryRun').onclick=()=>{const c=current.config;setPreferences(c);$('#symbol').value=c.symbol;$('#date').value=c.date;$('#depth').value=c.depth;$$('input[name="analyst"]').forEach(x=>x.checked=c.analysts.includes(x.value));$('#analysisDialog').showModal();};
$('#download').onclick=()=>{if(current)location.href=`/api/jobs/${current.id}/report`;};
$('.tabs').onkeydown=e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;const tabs=$$('[data-tab]').filter(b=>!b.disabled);const i=tabs.indexOf(document.activeElement);if(i<0)return;e.preventDefault();const next=e.key==='Home'?0:e.key==='End'?tabs.length-1:(i+(e.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;tabs[next].focus();tabs[next].click();};
const details=element('section',undefined,'card detail-reports');details.id='detailReports';$('.main-column').append(details);
async function init(){try{bootstrap=await api('/api/bootstrap');providerOptions($('#provider'));providerOptions($('#settingsProvider'));setPreferences(bootstrap.preferences||bootstrap.defaults);$('#date').value=bootstrap.today;$('#date').max=bootstrap.today;jobs=await api('/api/jobs');renderHistory();if(jobs.length)await openJob(jobs.find(active)?.id||jobs[0].id);else showView('research');$('#connectionMessage').hidden=true;}catch(e){text('#connectionMessage',e.message+' 잠시 후 자동으로 재연결합니다.');setTimeout(init,5000);}}
init();setInterval(refresh,2000);
