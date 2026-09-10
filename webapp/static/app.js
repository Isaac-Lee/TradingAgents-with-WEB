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
let bootstrap, current, jobs = [], activeTab = 'market', period = '1M', chartType = 'candle', view = 'research';
let polling = false, selectedInstrument = null;
function cleanInstrumentName(name) {
  let result=name||'종목';
  const suffix=/(?:[,\s]+)(?:co\.?[,]?\s*ltd\.?|incorporated|corporation|limited|inc\.?|corp\.?|ltd\.?|llc\.?|plc\.?|co\.?)\s*$/i;
  for(;;){const next=result.replace(suffix,'').replace(/[ ,.]+$/,'');if(!next||next===result)return result;result=next;}
}
const instrumentLabel = cfg => cleanInstrumentName(cfg.symbolName);
function applyAssetAnalysts(){const symbol=selectedInstrument?.symbol||$('#symbol').value.trim().toUpperCase();const unsupported=symbol.startsWith('^')||/-(USD[TC]?|BTC|ETH)$/.test(symbol);const box=$('input[name="analyst"][value="fundamentals"]');box.disabled=unsupported;if(unsupported)box.checked=false;}
const statuses = {queued:'대기 중',running:'분석 중',cancelling:'중지 요청됨',completed:'분석 완료',failed:'실행 실패',cancelled:'중지됨',interrupted:'서버 중단',imported:'가져온 보고서'};
const labels = {market:'시장 분석',fundamentals:'펀더멘털',news:'뉴스',sentiment:'시장 심리'};
const fields = {market:'market_report',fundamentals:'fundamentals_report',news:'news_report',sentiment:'sentiment_report'};
const stages = ['전문가 분석','리서치 토론','트레이더 전략','리스크 검토','최종 판단'];
const active = job => job && ['queued','running','cancelling'].includes(job.status);
const text = (selector, value) => { $(selector).textContent = value ?? '—'; };
function element(tag, value, className) { const el=document.createElement(tag);if(value!==undefined)el.textContent=value;if(className)el.className=className;return el; }
const indexFlags = {
  '^N225':['🇯🇵','일본'], '^TOPX':['🇯🇵','일본'],
  '^KS11':['🇰🇷','대한민국'], '^KQ11':['🇰🇷','대한민국'],
  '^GSPC':['🇺🇸','미국'], '^DJI':['🇺🇸','미국'], '^IXIC':['🇺🇸','미국'], '^NDX':['🇺🇸','미국'], '^RUT':['🇺🇸','미국'],
  '^FTSE':['🇬🇧','영국'], '^GDAXI':['🇩🇪','독일'], '^FCHI':['🇫🇷','프랑스'],
  '^HSI':['🇭🇰','홍콩'], '000001.SS':['🇨🇳','중국'], '399001.SZ':['🇨🇳','중국'],
  '^BSESN':['🇮🇳','인도'], '^NSEI':['🇮🇳','인도'], '^AXJO':['🇦🇺','호주'],
  '^GSPTSE':['🇨🇦','캐나다'], '^BVSP':['🇧🇷','브라질'], '^TWII':['🇹🇼','대만'],
  '^STI':['🇸🇬','싱가포르'], '^STOXX50E':['🇪🇺','유럽연합']
};
function setInstrumentIcon(target,cfg) {
  target.replaceChildren();target.classList.remove('has-logo');target.classList.add('instrument-icon');
  const flag=indexFlags[cfg.symbol];
  target.classList.toggle('index-icon',!!flag||cfg.symbol.startsWith('^'));
  if(flag||cfg.symbol.startsWith('^')){target.textContent=flag?.[0]||'🌐';target.setAttribute('aria-label',(flag?.[1]||'지수')+' 국기');return;}
  target.removeAttribute('aria-label');
  const fallback=element('span',cfg.symbol[0]);target.append(fallback);
  const img=document.createElement('img');img.alt='';img.hidden=true;img.decoding='async';
  img.onload=()=>{img.hidden=false;fallback.hidden=true;target.classList.add('has-logo');};
  img.onerror=()=>{img.remove();fallback.hidden=false;target.classList.remove('has-logo');};
  img.src='/api/logo?symbol='+encodeURIComponent(cfg.symbol);target.append(img);
}
function instrumentIcon(cfg,className){const target=element('span',undefined,className);setInstrumentIcon(target,cfg);return target;}
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
    const make=(cls)=>{const b=element('button',undefined,cls);b.append(instrumentIcon(cfg,'recent-icon'));const content=element('div',instrumentLabel(cfg));content.append(element('small',`${cfg.date} · ${statuses[job.status]||job.status}`));b.append(content);b.onclick=()=>openJob(job.id);return b;};
    if(index<5)$('#recent').append(make('recent-button'));
    const row=make('history-row');row.append(element('span',cfg.provider),element('span','보고서 보기 →'));$('#historyList').append(row);
  });text('#historyCount',jobs.length);
  $('#newAnalysis').disabled=jobs.some(active);
}
async function openJob(id) {try{current=await api('/api/jobs/'+id);render();showView('research');}catch(e){toast(e.message);} }
function renderChart() {
  const data=current.reports.market_data||{};
  const all=(data.bars||[]).filter(b=>Number.isFinite(b.close));
  const yearStart=new Date(current.config.date+'T00:00:00Z');yearStart.setUTCDate(yearStart.getUTCDate()-365);
  const bars=period==='1Y'?all.filter(b=>b.date>=yearStart.toISOString().slice(0,10)):all.slice(-({'1W':5,'1M':22,'3M':66}[period]));
  const hasOHLC=bars.length>0&&bars.every(b=>[b.open,b.high,b.low].every(Number.isFinite)&&b.low<=Math.min(b.open,b.close)&&b.high>=Math.max(b.open,b.close));
  const mode=chartType==='candle'&&bars.length&&!hasOHLC?'line':chartType;
  const chart=$('#chart'),tooltip=$('#chartTooltip');chart.replaceChildren();$('#chartLabels').replaceChildren();tooltip.hidden=true;tooltip.replaceChildren();
  chart.onpointermove=chart.onpointerleave=chart.onpointercancel=chart.onkeydown=chart.onfocus=chart.onblur=null;
  chart.setAttribute('tabindex',bars.length?'0':'-1');
  chart.setAttribute('aria-label',mode==='candle'?'기준일 이전 캔들 차트 · 초록 상승, 빨강 하락':'기준일 이전 종가 선 차트');
  chart.toggleAttribute('hidden',!bars.length);
  $$('[data-chart-type]').forEach(b=>{
    b.disabled=b.dataset.chartType==='candle'&&bars.length>0&&!hasOHLC;
    b.classList.toggle('selected',b.dataset.chartType===mode);
    b.setAttribute('aria-pressed',b.dataset.chartType===mode);
  });
  text('#marketSource',data.source||'미제공');
  text('#lastBar',all.at(-1)?.date);text('#volume',all.at(-1)?.volume?.toLocaleString());text('#currency',data.currency||'—');
  const notice=!bars.length?'저장된 가격 데이터가 없습니다.':!hasOHLC?'이 기록에는 종가만 저장되어 있어 선 차트로 표시합니다.':'';
  text('#chartNotice',notice);$('#chartNotice').hidden=!notice;
  $('#priceChange').classList.remove('negative');
  if(!bars.length){text('#price','—');text('#priceChange','가격 데이터 없음');text('.price-row small',current.source?'가져온 원문에는 별도 가격 시계열이 없습니다.':'가격 데이터 수집 전이거나 제공자에서 데이터를 반환하지 않았습니다.');return;}
  text('#price',bars.at(-1).close.toLocaleString(undefined,{maximumFractionDigits:2}));
  const delta=bars.at(-1).close-bars[0].close;const pct=bars[0].close?delta/bars[0].close*100:0;
  text('#priceChange',`${delta>=0?'↑':'↓'} ${delta.toFixed(2)} (${pct.toFixed(2)}%)`);
  $('#priceChange').classList.toggle('negative',delta<0);
  text('.price-row small',`${data.source||'저장된 가격'} · ${bars[0].date} ~ ${bars.at(-1).date} · ${data.currency||'통화 정보 없음'}`);
  const lo=Math.min(...bars.map(b=>mode==='candle'?b.low:b.close));
  const hi=Math.max(...bars.map(b=>mode==='candle'?b.high:b.close));
  const padding=(hi-lo||Math.abs(hi)*.02||1)*.12;
  const bottom=lo-padding,span=hi-lo+padding*2;
  const y=value=>165-(value-bottom)/span*150;
  const x=i=>12+(i+.5)*660/bars.length;
  function svg(tag,attrs,content){const node=document.createElementNS('http://www.w3.org/2000/svg',tag);Object.entries(attrs).forEach(([k,v])=>node.setAttribute(k,v));if(content!==undefined)node.textContent=content;chart.append(node);return node;}
  for(let i=0;i<4;i++){
    const value=bottom+span*i/3,yy=y(value);
    svg('line',{x1:12,x2:680,y1:yy,y2:yy,'class':'chart-grid'});
    svg('text',{x:694,y:yy+4,'font-size':10},value.toLocaleString(undefined,{maximumFractionDigits:2}));
  }
  if(mode==='candle'){
    const width=Math.max(1,Math.min(14,660/bars.length*.65));
    bars.forEach((b,i)=>{
      const color=b.close>=b.open?'var(--candle-up)':'var(--candle-down)';
      svg('path',{d:`M${x(i)},${y(b.high)} V${y(b.low)}`,stroke:color,'stroke-width':1.5,'class':'candle-wick'});
      svg('rect',{x:x(i)-width/2,y:Math.min(y(b.open),y(b.close)),width,height:Math.max(1.5,Math.abs(y(b.open)-y(b.close))),rx:1,fill:color,'class':'candle-body'});

    });
  }else{
    const line=bars.map((b,i)=>(i?'L':'M')+`${x(i)},${y(b.close)}`).join(' ');
    svg('path',{d:`${line} L${x(bars.length-1)},165 L${x(0)},165 Z`,fill:'var(--green-soft)'});
    svg('path',{d:line,fill:'none',stroke:'var(--chart-line)','stroke-width':2.5,'class':'price-line'});
    if(bars.length===1)svg('circle',{cx:x(0),cy:y(bars[0].close),r:3,fill:'var(--chart-line)'});
  }
  // Match the reference dashboard's two-column tooltip and edge-aware placement.
  const vertical=svg('path',{'class':'chart-crosshair',hidden:''});
  const horizontal=svg('path',{'class':'chart-crosshair',hidden:''});
  const marker=svg('circle',{'class':'chart-hover-point',r:3.5,hidden:''});
  svg('rect',{x:12,y:15,width:660,height:150,fill:'transparent','class':'chart-hit-area'});
  let selected=bars.length-1;
  const format=value=>Number.isFinite(value)?value.toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2}):'—';
  function hideTooltip(){tooltip.hidden=true;[vertical,horizontal,marker].forEach(n=>n.setAttribute('hidden',''));}
  function showTooltip(index,clientX,clientY){
    selected=Math.max(0,Math.min(bars.length-1,index));
    const bar=bars[selected],xx=x(selected),yy=y(bar.close);
    vertical.setAttribute('d',`M${xx},15 V165`);horizontal.setAttribute('d',`M12,${yy} H680`);
    marker.setAttribute('cx',xx);marker.setAttribute('cy',yy);
    [vertical,horizontal,marker].forEach(n=>n.removeAttribute('hidden'));
    tooltip.replaceChildren();
    const heading=element('div',undefined,'chart-tooltip-heading');heading.append(element('strong',bar.date),element('span',data.currency||''));tooltip.append(heading);
    const rows=mode==='candle'?[['시가',bar.open],['고가',bar.high],['저가',bar.low],['종가',bar.close]]:[['종가',bar.close]];
    rows.forEach(([label,value])=>{const row=element('div',undefined,'chart-tooltip-row');row.append(element('span',label),element('strong',format(value)));tooltip.append(row);});
    if(Number.isFinite(bar.volume)){const row=element('div',undefined,'chart-tooltip-row chart-tooltip-volume');row.append(element('span','거래량'),element('strong',bar.volume.toLocaleString()));tooltip.append(row);}
    tooltip.hidden=false;
    const wrap=tooltip.parentElement.getBoundingClientRect();
    if(clientX===undefined){const point=new DOMPoint(xx,yy).matrixTransform(chart.getScreenCTM());clientX=point.x;clientY=point.y;}
    const px=clientX-wrap.left,py=clientY-wrap.top,gap=14;
    const width=tooltip.offsetWidth,height=tooltip.offsetHeight;
    const left=px+gap+width>wrap.width?px-width-gap:px+gap;
    const top=py+gap+height>wrap.height?py-height-gap:py+gap;
    tooltip.style.left=Math.max(0,Math.min(left,wrap.width-width))+'px';
    tooltip.style.top=Math.max(0,Math.min(top,wrap.height-height))+'px';
  }
  chart.onpointermove=event=>{
    const matrix=chart.getScreenCTM();if(!matrix)return;
    const point=new DOMPoint(event.clientX,event.clientY).matrixTransform(matrix.inverse());
    if(point.x<12||point.x>672||point.y<15||point.y>165){hideTooltip();return;}
    showTooltip(Math.floor((point.x-12)/660*bars.length),event.clientX,event.clientY);
  };
  chart.onpointerleave=chart.onpointercancel=chart.onblur=hideTooltip;
  chart.onfocus=()=>showTooltip(selected);
  chart.onkeydown=event=>{
    if(event.key==='Escape'){hideTooltip();return;}
    if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
    event.preventDefault();showTooltip(event.key==='Home'?0:event.key==='End'?bars.length-1:selected+(event.key==='ArrowRight'?1:-1));
  };
  [...new Set([bars[0].date,bars[Math.floor(bars.length/2)].date,bars.at(-1).date])].forEach(d=>$('#chartLabels').append(element('span',d)));
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
  text('#stockName',instrumentLabel(cfg));text('#ticker','');setInstrumentIcon($('#stockLogo'),cfg);
  text('#stockMeta',`${cfg.provider} · 기준일 ${cfg.date}`);text('#analysisDate',cfg.date);
  text('#runStatus',statuses[current.status]);text('#sourceLabel',current.source?(cfg.provider==='Local reports'?'로컬 보고서':'외부 보고서'):'웹 분석');
  const sourceUrl=current.source&&/^https:\/\/github\.com\//.test(current.source)?current.source:null;
  $('#sourceLink').hidden=!sourceUrl;
  if(sourceUrl)$('#sourceLink').href=sourceUrl;else $('#sourceLink').removeAttribute('href');
  const notice=current.error||(current.status==='cancelling'?'현재 모델 호출이 끝나는 다음 단계에서 중지됩니다.':current.source?`${cfg.provider==='Local reports'?'로컬 파일':cfg.provider}에서 가져온 AI 분석 원문입니다. 보고서의 주장은 별도로 검증하지 않았으며 현재 시세를 의미하지 않습니다.`:'');
  $('#jobNotice').hidden=!notice;text('#jobNotice',notice);
  $('#cancelRun').hidden=!active(current);$('#cancelRun').disabled=current.status==='cancelling';
  $('#retryRun').hidden=active(current)||!!current.source;
  $('#deleteReport').hidden=!['imported','interrupted','cancelled','failed'].includes(current.status);
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
// Custom listboxes retain the native fields as the form's value source.
let openChoice = null;
const choiceLabels = [];
function refreshChoiceLabels() { choiceLabels.forEach(update => update()); }
function setupChoices() {
  ['provider','settingsProvider','depth','runQuick','runDeep','quickModel','deepModel','symbol'].forEach(id => {
    const field = $('#'+id), editable = field.tagName === 'INPUT', isSymbol = id === 'symbol';
    const label = field.closest('label').firstChild.textContent.trim();
    const wrap = element('div', undefined, 'choice-control');
    field.replaceWith(wrap);wrap.append(field);
    field.removeAttribute('list');
    let control = field;
    if (!editable) {
      field.hidden = true;
      control = element('button', undefined, 'choice-trigger');control.type = 'button';wrap.append(control);
      const update = () => { control.textContent = field.selectedOptions[0]?.textContent || ''; };
      choiceLabels.push(update);field.addEventListener('change', update);update();
    } else { field.autocomplete='off';field.spellcheck=false; }
    control.setAttribute('role','combobox');control.setAttribute('aria-label',label);
    control.setAttribute('aria-haspopup','listbox');control.setAttribute('aria-expanded','false');
    if (editable) control.setAttribute('aria-autocomplete','list');
    const menu = element('div', undefined, 'choice-menu');menu.id=id+'-choices';
    menu.setAttribute('role','listbox');menu.setAttribute('aria-label',label);
    menu.setAttribute('popover','manual');wrap.append(menu);
    control.setAttribute('aria-controls',menu.id);
    let options=[],highlight=-1,opened=false,symbolMatches=[],searchTimer,searchVersion=0;
    let emptyMessage='종목명 또는 티커로 검색하세요.';
    function entries() {
      if(isSymbol)return symbolMatches.map(q=>[cleanInstrumentName(q.name),q.symbol,[q.exchange,q.type].filter(Boolean).join(' · ')]);
      if (!editable) return [...field.options].filter(o=>!o.disabled).map(o=>[o.textContent,o.value]);
      const provider=$('#'+(id==='quickModel'||id==='deepModel'?'settingsProvider':'provider')).value;
      const mode=id==='runQuick'||id==='quickModel'?'quick':'deep';
      return (bootstrap?.providers.find(p=>p.id===provider)?.[mode]||[]).filter(([,value])=>value!=='custom');
    }
    function close() {
      if(isSymbol){clearTimeout(searchTimer);searchVersion++;}
      if (!opened) return;
      opened=false;menu.hidePopover();control.setAttribute('aria-expanded','false');
      control.removeAttribute('aria-activedescendant');if(openChoice?.menu===menu)openChoice=null;
    }
    function highlightOption(index) {
      highlight=index;
      [...menu.querySelectorAll('[role="option"]')].forEach((node,i)=>node.classList.toggle('highlighted',i===index));
      const selected=menu.querySelectorAll('[role="option"]')[index];
      if(selected){control.setAttribute('aria-activedescendant',selected.id);selected.scrollIntoView({block:'nearest'});}
      else control.removeAttribute('aria-activedescendant');
    }
    function choose(index) {
      if (!options[index]) return;
      field.value=options[index][1];
      if(isSymbol){selectedInstrument=symbolMatches.find(q=>q.symbol===field.value);field.value=instrumentLabel({symbol:selectedInstrument.symbol,symbolName:selectedInstrument.name});field.setCustomValidity('');applyAssetAnalysts();}
      field.dispatchEvent(new Event('change',{bubbles:true}));
      refreshChoiceLabels();close();control.focus();
    }
    function position() {
      const rect=control.getBoundingClientRect(),gap=7,edge=12;
      const below=window.innerHeight-rect.bottom-gap-edge,above=rect.top-gap-edge;
      const up=below<180&&above>below,room=Math.max(60,up?above:below);
      menu.style.width=Math.min(Math.max(rect.width,isSymbol?420:240),window.innerWidth-edge*2)+'px';
      menu.style.maxHeight=Math.min(290,room)+'px';
      menu.style.left=Math.max(edge,Math.min(rect.left,window.innerWidth-menu.offsetWidth-edge))+'px';
      menu.style.top=(up?Math.max(edge,rect.top-gap-menu.offsetHeight):rect.bottom+gap)+'px';
    }
    function open(filter=false) {
      if(openChoice?.menu!==menu)openChoice?.close();
      const query=filter?field.value.trim().toLowerCase():'';
      options=entries().filter(([title,value])=>!query||(title+' '+value).toLowerCase().includes(query));
      menu.replaceChildren();
      options.forEach(([title,value,detail],i)=>{
        const option=element('div',undefined,'choice-option');option.id=menu.id+'-'+i;
        option.setAttribute('role','option');option.setAttribute('aria-selected',(isSymbol?selectedInstrument?.symbol:field.value)===value);
        const content=element('span',editable&&!isSymbol?value:title,'choice-option-text');
        if(isSymbol&&detail)content.append(element('small',detail));else if(editable&&!isSymbol&&title!==value)content.append(element('small',title));
        if(isSymbol)option.append(instrumentIcon({symbol:value},'search-symbol-icon'));
        option.append(content,element('span',(isSymbol?selectedInstrument?.symbol:field.value)===value?'✓':'','choice-check'));
        option.onpointerdown=e=>e.preventDefault();option.onclick=e=>{e.preventDefault();e.stopPropagation();choose(i);};menu.append(option);
      });
      if(!options.length)menu.append(element('p',isSymbol?emptyMessage:'목록에 없는 모델은 입력한 ID를 그대로 사용합니다.','choice-empty'));
      if(!opened){menu.showPopover();opened=true;}
      openChoice={menu,wrap,close,position};control.setAttribute('aria-expanded','true');
      position();highlightOption(options.findIndex(([,value])=>value===(isSymbol?selectedInstrument?.symbol:field.value)));
    }
    async function searchSymbol() {
      const query=field.value.trim(),version=++searchVersion;
      if(!query){symbolMatches=[];emptyMessage='종목명 또는 티커로 검색하세요.';open();return;}
      symbolMatches=[];emptyMessage='Yahoo Finance에서 검색 중…';open();
      try {
        const response=await api('/api/symbols?q='+encodeURIComponent(query));
        if(version!==searchVersion||field.value.trim()!==query)return;
        symbolMatches=response.results;emptyMessage='검색 결과가 없습니다. 영문 종목명이나 티커로 다시 검색하세요.';
      }catch(error){if(version!==searchVersion)return;emptyMessage='검색에 연결하지 못했습니다. 잠시 후 다시 검색하세요.';}
      if(document.activeElement===field)open();
    }
    control.addEventListener('click',()=>{if(opened)close();else if(isSymbol&&!selectedInstrument)searchSymbol();else open();});
    if(editable)control.addEventListener('input',()=>{
      if(!isSymbol){open(true);return;}
      selectedInstrument=null;applyAssetAnalysts();searchVersion++;clearTimeout(searchTimer);
      const value=field.value.trim();
      field.setCustomValidity(value?'검색 결과에서 종목을 선택하세요.':'');
      close();searchTimer=setTimeout(searchSymbol,300);
    });
    control.addEventListener('keydown',e=>{
      if(e.key==='Escape'&&opened){e.preventDefault();e.stopPropagation();close();return;}
      if(e.key==='Tab'){close();return;}
      if(['ArrowDown','ArrowUp'].includes(e.key)){
        e.preventDefault();if(!opened)open();
        if(options.length)highlightOption((highlight+(e.key==='ArrowDown'?1:-1)+options.length)%options.length);
      }else if(opened&&['Home','End'].includes(e.key)&&!editable){e.preventDefault();highlightOption(e.key==='Home'?0:options.length-1);}
      else if(opened&&e.key==='Enter'){e.preventDefault();if(highlight>=0)choose(highlight);else close();}
      else if(!editable&&e.key.length===1&&e.key!==' '){e.preventDefault();if(!opened)open();highlightOption(options.findIndex(([title])=>title.toLowerCase().startsWith(e.key.toLowerCase())));}
    });
    wrap.addEventListener('focusout',e=>{if(!wrap.contains(e.relatedTarget))close();});
  });
  document.addEventListener('pointerdown',e=>{if(openChoice&&!openChoice.wrap.contains(e.target))openChoice.close();});
  document.addEventListener('scroll',e=>{if(openChoice&&!openChoice.menu.contains(e.target))openChoice.close();},true);
  window.addEventListener('resize',()=>openChoice?.close());
  $('#analysisDialog').addEventListener('close',()=>openChoice?.close());
}

function providerOptions(select) {select.replaceChildren();bootstrap.providers.forEach(p=>{const o=element('option',p.label);o.value=p.id;select.append(o);});refreshChoiceLabels();}
function modelOptions(provider,quick,deep) {
  const p=bootstrap.providers.find(x=>x.id===provider);if(!p)return;
  [['quick',quick],['deep',deep]].forEach(([mode,input])=>{const list=$('#'+mode+'Options');list.replaceChildren();p[mode].filter(([,id])=>id!=='custom').forEach(([label,id])=>{const o=element('option',label);o.value=id;list.append(o);});input.value=p[mode].find(([,id])=>id!=='custom')?.[1]||'';});
}
function setPreferences(p) {$('#provider').value=p.provider;$('#settingsProvider').value=p.provider;modelOptions(p.provider,$('#runQuick'),$('#runDeep'));$('#quickModel').value=p.quickModel;$('#deepModel').value=p.deepModel;$('#runQuick').value=p.quickModel;$('#runDeep').value=p.deepModel;providerStatus();refreshChoiceLabels();}
function providerStatus() {const p=bootstrap.providers.find(x=>x.id===$('#settingsProvider').value);text('#providerStatus',p.configured===false?`설정 필요: ${p.key_env||'Codex CLI 설치 및 로그인'}`:p.id==='codex'?'Codex CLI 감지됨 · 구독 로그인 여부는 실행 시 확인합니다.':p.configured?'서버 인증 환경변수가 설정되어 있습니다.':'서버의 제공자 인증 또는 로컬 엔드포인트를 사용합니다.');}
function formConfig() {return {symbol:selectedInstrument?.symbol||$('#symbol').value.trim(),symbolName:selectedInstrument?.name||'',date:$('#date').value,provider:$('#provider').value,quickModel:$('#runQuick').value.trim(),deepModel:$('#runDeep').value.trim(),depth:Number($('#depth').value),analysts:$$('input[name="analyst"]:checked').map(x=>x.value)};}
async function refresh() {
  if(polling||!bootstrap)return;polling=true;
  try {jobs=await api('/api/jobs');renderHistory();if(current){const record=jobs.find(j=>j.id===current.id);if(record&&(record.updated!==current.updated||active(current))){current=await api('/api/jobs/'+current.id);render();}}text('#connectionMessage','');$('#connectionMessage').hidden=true;}
  catch(e){$('#connectionMessage').hidden=false;text('#connectionMessage','서버 연결이 끊겼습니다. 다시 연결을 시도합니다. 기록은 서버에 저장되어 있습니다.');}
  finally{polling=false;}
}
$$('.nav').forEach(b=>b.onclick=()=>showView(b.dataset.view));
$$('[data-tab]').forEach(b=>b.onclick=()=>{activeTab=b.dataset.tab;renderReport();});
$$('[data-period]').forEach(b=>b.onclick=()=>{period=b.dataset.period;$$('[data-period]').forEach(x=>{x.classList.toggle('selected',x===b);x.setAttribute('aria-pressed',x===b);});renderChart();});
$$('[data-chart-type]').forEach(b=>b.onclick=()=>{chartType=b.dataset.chartType;renderChart();});
$('#newAnalysis').onclick=()=>{if(!bootstrap)return;$('#formError').textContent='';refreshChoiceLabels();$('#analysisDialog').showModal();};
$('#closeDialog').onclick=()=>$('#analysisDialog').close();
$('#provider').onchange=()=>modelOptions($('#provider').value,$('#runQuick'),$('#runDeep'));

$('#settingsProvider').onchange=()=>{modelOptions($('#settingsProvider').value,$('#quickModel'),$('#deepModel'));providerStatus();};
$('#saveSettings').onclick=async()=>{try{const config={...formConfig(),symbol:'SPY',symbolName:'',date:bootstrap.today,analysts:['market'],provider:$('#settingsProvider').value,quickModel:$('#quickModel').value,deepModel:$('#deepModel').value};await api('/api/preferences',config);setPreferences(config);toast('기본 모델 설정을 저장했습니다.');}catch(e){toast(e.message);}};
$('#analysisForm').onsubmit=async e=>{e.preventDefault();const submit=$('#analysisForm button[type="submit"]');submit.disabled=true;try{current=await api('/api/jobs',formConfig());$('#analysisDialog').close();render();showView('research');await refresh();}catch(error){text('#formError',error.message);}finally{submit.disabled=false;}};
let pendingDeleteId=null;
$('#deleteReport').onclick=()=>{if(!['imported','interrupted','cancelled','failed'].includes(current?.status))return;pendingDeleteId=current.id;text('#deleteReportName',instrumentLabel(current.config));$('#deleteDialog').showModal();};
$('#cancelDelete').onclick=()=>$('#deleteDialog').close();
$('#confirmDelete').onclick=async()=>{
  if(!pendingDeleteId)return;
  const id=pendingDeleteId,button=$('#confirmDelete');button.disabled=true;
  try {
    await api(`/api/jobs/${id}/delete`,{});
    $('#deleteDialog').close();pendingDeleteId=null;
    if(current?.id===id)current=null;
    await refresh();showView('history');toast('보고서를 삭제했습니다.');
  }catch(error){toast(error.message);}finally{button.disabled=false;}
};
$('#cancelRun').onclick=async()=>{try{current=await api(`/api/jobs/${current.id}/cancel`,{});render();}catch(e){toast(e.message);}};
$('#retryRun').onclick=()=>{const c=current.config;setPreferences(c);selectedInstrument=c.symbolName?{symbol:c.symbol,name:c.symbolName}:null;$('#symbol').value=instrumentLabel(c);$('#symbol').setCustomValidity('');$('#date').value=c.date;$('#depth').value=c.depth;$$('input[name="analyst"]').forEach(x=>x.checked=c.analysts.includes(x.value));applyAssetAnalysts();refreshChoiceLabels();$('#analysisDialog').showModal();};
$('#download').onclick=()=>{if(current)location.href=`/api/jobs/${current.id}/report`;};
$('.tabs').onkeydown=e=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(e.key))return;const tabs=$$('[data-tab]').filter(b=>!b.disabled);const i=tabs.indexOf(document.activeElement);if(i<0)return;e.preventDefault();const next=e.key==='Home'?0:e.key==='End'?tabs.length-1:(i+(e.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;tabs[next].focus();tabs[next].click();};
const details=element('section',undefined,'card detail-reports');details.id='detailReports';$('.main-column').append(details);
async function init(){try{bootstrap=await api('/api/bootstrap');providerOptions($('#provider'));providerOptions($('#settingsProvider'));setPreferences(bootstrap.preferences||bootstrap.defaults);$('#date').value=bootstrap.today;$('#date').max=bootstrap.today;jobs=await api('/api/jobs');renderHistory();if(jobs.length)await openJob(jobs.find(active)?.id||jobs[0].id);else showView('research');$('#connectionMessage').hidden=true;}catch(e){text('#connectionMessage',e.message+' 잠시 후 자동으로 재연결합니다.');setTimeout(init,5000);}}
setupChoices();init();setInterval(refresh,2000);
