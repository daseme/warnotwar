// Teaching-module dataset. Loaded before shared.js; shared.js keeps
// only rendering and state.
//
// THIS IS A SIMULATION. The five dates, prices and readings are a
// constructed teaching scenario shaped like the real 2026 episode but
// not the live record. Sources on ledger items are marked illustrative.
// A live series can replace this file when the pipeline lands (Phase 3).
const SERIES = {
  id: 'sim-spring-2026',
  kind: 'simulation',
  label: 'Simulation — illustrative figures',
  note: 'A constructed teaching scenario, not the live record. The real, sourced data lives at warnotwar.com/oilflows.html.',
};

const dates = [
  { id:'feb23', label:'Feb 23', brent:71.90, bno:32.15, hormuz:123, buffer:58, news:'Normal traffic', yanbu:105, fujairah:98 },
  { id:'mar02', label:'Mar 2',  brent:77.24, bno:34.80, hormuz:72,  buffer:55, news:'Traffic falling', yanbu:118, fujairah:85 },
  { id:'mar07', label:'Mar 7',  brent:95.74, bno:43.95, hormuz:2.8, buffer:42, news:'Near-total halt', yanbu:137, fujairah:62 },
  { id:'mar12', label:'Mar 12', brent:102.38,bno:47.20, hormuz:0.9, buffer:40, news:'Still blocked',   yanbu:142, fujairah:55 },
  { id:'apr07', label:'Apr 7',  brent:138.21,bno:62.50, hormuz:8,   buffer:38, news:'Partial reopen',  yanbu:125, fujairah:78 },
];

const items = [
  { id:'c1', check:'Not checkable against public data; the observations behind it are not public.', differs:'c2', speaker:'U.S. officials', date:'2026-03-07', lo:10, hi:12, unit:'mbd', scope:'hormuz_outbound', period:'unspecified', commodity:'unspecified', evidence:'government_estimate', quote:'Approximately 10 to 12 million barrels per day of oil flow through the Strait of Hormuz', source:'illustrative', url:'#', kind:'claim', attribution:'anonymous' },
  { id:'c2', check:'A model estimate; checkable against later official export data.', differs:'c1', speaker:'Commercial trackers', date:'2026-03-07', lo:5, hi:6, unit:'mbd', scope:'hormuz_outbound', period:'seven_day_average', commodity:'crude_condensate', evidence:'commercial_tracker_model', quote:'Model-based estimate of Hormuz outbound crude plus condensate', source:'illustrative', url:'#', kind:'estimate', attribution:'named' },
  { id:'c3', check:'Matches ship tracking, but it counts activity, never barrels.', speaker:'A ship-tracking index', date:'2026-03-07', lo:2.8, hi:2.8, unit:'tankers_per_night', scope:'ship_transits_in_and_out', period:'nightly', commodity:'unspecified', evidence:'activity_index', quote:'AIS-visible tanker transits through Hormuz corridor', source:'illustrative', url:'#', kind:'claim', attribution:'named' },
  { id:'c4', check:'A single-day figure; checkable against loadings data when published.', speaker:'An analyst', date:'2026-03-07', lo:18, hi:18, unit:'mbbl_single_day', scope:'hormuz_outbound', period:'single_day', commodity:'all_liquids', evidence:'government_estimate', quote:'18 million barrels moved on March 6', source:'illustrative', url:'#', kind:'claim', attribution:'named' },
  { id:'c5', check:'Not checkable against public data; no independent count of the whole region exists.', speaker:'U.S. officials', date:'2026-03-07', lo:14, hi:16, unit:'mbd', scope:'regional_total_including_bypass', period:'unspecified', commodity:'unspecified', evidence:'government_estimate', quote:'About 14 to 16 million barrels per day leave the region when bypass pipelines are counted', source:'illustrative', url:'#', kind:'claim', attribution:'anonymous' },
];

const SCOPE = { hormuz_outbound:'through the Strait of Hormuz only', regional_total_including_bypass:'the whole region, including bypass pipelines', ship_transits_in_and_out:'ship movements at the strait, in both directions' };
const WINDOW = { seven_day_average:'a 7-day average', single_day:'one single day', nightly:'per night', unspecified:'the speaker did not state a time window' };
const COMM = { crude:'crude oil', crude_condensate:'crude oil plus condensate', all_liquids:'all petroleum liquids', unspecified:'oil flow — commodity not stated' };
const EVIDENCE = { government_estimate:'U.S. government estimate — underlying observations not public', commercial_tracker_model:'a commercial tracker\u2019s model, reaching us secondhand through the press', activity_index:'ship-signal activity index — never barrels' };


// Only factual reads of the freeze frame are ever scored; causal
// attribution has no answer key and is shown unscored after the reveal.
const chalReasonsList = [
  {key:'flow',label:'Hormuz activity is below 15% of baseline',label5:'Ship traffic is below 15% of normal',correct:d=>d.hormuz<15},
  {key:'bypass',label:'Yanbu activity is above its baseline',label5:'Yanbu is busier than normal',correct:d=>d.yanbu>110},
  {key:'buffer',label:'The cushion is below 45 days',label5:'The oil cushion is below 45 days',correct:d=>d.buffer<45},
  {key:'brent',label:'Brent is up more than 25% from Feb 23',label5:'The oil price is up more than 25% since Feb 23',correct:d=>d.brent>89.9},
  {key:'calm',label:'Hormuz activity is above half of baseline',label5:'Ship traffic is above half of normal',correct:d=>d.hormuz>50}
];


// Story mode: titles/subtitles/signal frames only. Signal VALUES derive
// from `dates` so the two can never drift again.
const storyMeta = {
  feb23: { title:'The Calm Before', subtitle:'Tanker traffic through Hormuz is normal. The market is relaxed.', signals:[
    {icon:'\u{1F6A2}',title:'Hormuz traffic',desc:'Tanker traffic at its normal level',valueFrom:'hormuz',color:'rgba(63,185,80,0.15)',textColor:'#3fb950'},
    {icon:'\u{1F6E2}\uFE0F',title:'Oil cushion',desc:'Plenty of stored oil',valueFrom:'buffer',color:'rgba(63,185,80,0.15)',textColor:'#3fb950'},
    {icon:'\u{1F4F0}',title:'News',desc:'Nothing unusual reported',value:'Calm',color:'rgba(255,255,255,0.06)',textColor:'var(--text-secondary)'}]},
  mar02: { title:'The First Rattle', subtitle:'Traffic starts falling. Traders begin to notice.', signals:[
    {icon:'\u{1F6A2}',title:'Hormuz traffic',desc:'Tanker traffic falling fast',valueFrom:'hormuz',color:'rgba(210,153,34,0.15)',textColor:'#d29922'},
    {icon:'\u{1F6E2}\uFE0F',title:'Oil cushion',desc:'Still okay, but shrinking',valueFrom:'buffer',color:'rgba(210,153,34,0.15)',textColor:'#d29922'},
    {icon:'\u{1F4F0}',title:'News',desc:'Reports of rising tensions in the Gulf',value:'Concern',color:'rgba(210,153,34,0.15)',textColor:'#d29922'}]},
  mar07: { title:'The Halt', subtitle:'Hormuz traffic collapses. In this scenario, prices jump sharply.', signals:[
    {icon:'\u{1F6A2}',title:'Hormuz traffic',desc:'Ship traffic has almost stopped',valueFrom:'hormuz',color:'rgba(248,81,73,0.15)',textColor:'#f85149'},
    {icon:'\u{1F6E2}\uFE0F',title:'Oil cushion',desc:'Lower than usual. Not much to spare.',valueFrom:'buffer',color:'rgba(248,81,73,0.15)',textColor:'#f85149'},
    {icon:'\u{1F4F0}',title:'News',desc:'Officials say most oil still flows; independent trackers see far less.',value:'Crisis',color:'rgba(248,81,73,0.15)',textColor:'#f85149'},
    {icon:'\u{1F504}',title:'Bypass routes',desc:'Yanbu and Fujairah busier, but not enough',valueFrom:'yanbuDelta',color:'rgba(88,166,255,0.15)',textColor:'#58a6ff'}]},
  mar12: { title:'The Standstill', subtitle:'The strait is effectively closed. Prices keep climbing.', signals:[
    {icon:'\u{1F6A2}',title:'Hormuz traffic',desc:'Almost no ships moving',valueFrom:'hormuz',color:'rgba(248,81,73,0.15)',textColor:'#f85149'},
    {icon:'\u{1F6E2}\uFE0F',title:'Oil cushion',desc:'Very low in this scenario.',valueFrom:'buffer',color:'rgba(248,81,73,0.15)',textColor:'#f85149'},
    {icon:'\u{1F4F0}',title:'News',desc:'Navy escorts announced. The strait stays shut.',value:'Severe',color:'rgba(248,81,73,0.15)',textColor:'#f85149'},
    {icon:'\u{1F504}',title:'Bypass routes',desc:'Bypass routes are maxed out in this scenario — still less than Hormuz carried.',value:'Max',color:'rgba(88,166,255,0.15)',textColor:'#58a6ff'}]},
  apr07: { title:'The Peak', subtitle:'Partial reopening begins; prices peak in this scenario.', signals:[
    {icon:'\u{1F6A2}',title:'Hormuz traffic',desc:'A little traffic returning. Recovery is slow.',valueFrom:'hormuz',color:'rgba(210,153,34,0.15)',textColor:'#d29922'},
    {icon:'\u{1F6E2}\uFE0F',title:'Oil cushion',desc:'Used up. Takes months to refill.',valueFrom:'buffer',color:'rgba(248,81,73,0.15)',textColor:'#f85149'},
    {icon:'\u{1F4F0}',title:'News',desc:'Peace talks under way. The market is not convinced.',value:'Tense',color:'rgba(210,153,34,0.15)',textColor:'#d29922'},
    {icon:'\u{1F4C8}',title:'Brent peak',desc:'Highest price since the crisis began.',valueFrom:'brent',color:'rgba(248,81,73,0.15)',textColor:'#f85149'}]},
};
function _sigVal(d, s) {
  switch (s.valueFrom) {
    case 'hormuz': return d.hormuz + '%';
    case 'buffer': return d.buffer + ' days';
    case 'brent': return '$' + d.brent.toFixed(2);
    case 'yanbuDelta': return '+' + Math.round(d.yanbu - 100) + '%';
    default: return s.value;
  }
}
const storyChapters = dates.map(d => {
  const m = storyMeta[d.id];
  return { ...d, title: m.title, subtitle: m.subtitle,
    signals: m.signals.map(s => ({ ...s, value: _sigVal(d, s) })) };
});

// FROM THE LIVE INVESTIGATION (not the simulation): the parent site's
// candidate explanations for the real 2026 tension. Rendered only inside
// live-record styled components. Independent plausibilities — these are
// not exclusive outcomes and must never be forced to sum to anything.
const liveCandidates = [
  { key:'demand',   label:'Demand destruction',                            explains:'the price',                 disc:'EIA products-supplied data — published weekly' },
  { key:'bypass',   label:'Bypass routes carrying more than modeled',      explains:'the flow reading',          disc:'Yanbu terminal-activity index — an activity signal, not barrels' },
  { key:'spr',      label:'Strategic releases bridging supply',            explains:'the cushion and the price', disc:'EIA weekly SPR data — observable now' },
  { key:'official', label:'The official flow figures being accurate',      explains:'the flow reading',          disc:'official export data, ~Oct–Nov 2026 — the referee' },
  { key:'deesc',    label:'Expectations of de-escalation priced in',       explains:'the price',                 disc:'not directly measurable; resolves only in hindsight' },
];
