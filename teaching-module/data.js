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
  { id:'c1', speaker:'U.S. officials', date:'2026-03-07', lo:9, hi:10, unit:'mbd', scope:'hormuz_outbound', period:'unspecified', commodity:'unspecified', evidence:'government_estimate', quote:'Approximately 9 to 10 million barrels per day of oil flow through the Strait of Hormuz', source:'illustrative', url:'#', kind:'claim', attribution:'anonymous' },
  { id:'c2', speaker:'Commercial trackers', date:'2026-03-07', lo:4.5, hi:5.5, unit:'mbd', scope:'hormuz_outbound', period:'seven_day_average', commodity:'crude_condensate', evidence:'commercial_tracker_model', quote:'Model-based estimate of Hormuz outbound crude plus condensate', source:'illustrative', url:'#', kind:'estimate', attribution:'named' },
  { id:'c3', speaker:'A ship-tracking index', date:'2026-03-07', lo:2.8, hi:2.8, unit:'tankers_per_night', scope:'ship_transits_in_and_out', period:'nightly', commodity:'unspecified', evidence:'activity_index', quote:'AIS-visible tanker transits through Hormuz corridor', source:'illustrative', url:'#', kind:'claim', attribution:'named' },
  { id:'c4', speaker:'An analyst', date:'2026-03-07', lo:15, hi:15, unit:'mbbl_single_day', scope:'hormuz_outbound', period:'single_day', commodity:'all_liquids', evidence:'government_estimate', quote:'15 million barrels moved on March 6', source:'illustrative', url:'#', kind:'claim', attribution:'named' },
];

const SCOPE = { hormuz_outbound:'through the Strait of Hormuz only', regional_total_including_bypass:'the whole region, including bypass pipelines', ship_transits_in_and_out:'ship movements at the strait, in both directions' };
const WINDOW = { seven_day_average:'a 7-day average', single_day:'one single day', nightly:'per night', unspecified:'the speaker did not state a time window' };
const COMM = { crude:'crude oil', crude_condensate:'crude oil plus condensate', all_liquids:'all petroleum liquids', unspecified:'oil flow — commodity not stated' };
const EVIDENCE = { government_estimate:'U.S. government estimate — underlying observations not public', commercial_tracker_model:'commercial tracker model — reaches us secondhand via press', activity_index:'ship-signal activity index — never barrels' };


const chalReasonsList = [
  {key:'flow',label:'Hormuz disruption is severe',correct:d=>d.hormuz<15},
  {key:'bypass',label:'Bypass routes are compensating',correct:d=>d.yanbu>120},
  {key:'buffer',label:'Inventories are dangerously low',correct:d=>d.buffer<45},
  {key:'expect',label:'Market is pricing in sustained scarcity',correct:d=>d.hormuz<20&&d.buffer<50},
  {key:'brent',label:'Brent has already moved sharply',correct:d=>d.brent>90},
  {key:'calm',label:'The situation is stabilizing',correct:d=>d.hormuz>50}
];


// Story mode: titles/subtitles/signal frames only. Signal VALUES derive
// from `dates` so the two can never drift again.
const storyMeta = {
  feb23: { title:'The Calm Before', subtitle:'Tanker traffic through Hormuz is normal. The market is relaxed.', signals:[
    {icon:'\u{1F6A2}',title:'Hormuz traffic',desc:'Visible tanker transits at baseline levels',valueFrom:'hormuz',color:'rgba(63,185,80,0.15)',textColor:'#3fb950'},
    {icon:'\u{1F6E2}\uFE0F',title:'Oil cushion',desc:'U.S. combined stocks at comfortable levels',valueFrom:'buffer',color:'rgba(63,185,80,0.15)',textColor:'#3fb950'},
    {icon:'\u{1F4F0}',title:'News',desc:'No significant supply disruptions reported',value:'Calm',color:'rgba(255,255,255,0.06)',textColor:'var(--text-secondary)'}]},
  mar02: { title:'The First Rattle', subtitle:'Traffic starts falling. Traders begin to notice.', signals:[
    {icon:'\u{1F6A2}',title:'Hormuz traffic',desc:'Visible transits down sharply from baseline',valueFrom:'hormuz',color:'rgba(210,153,34,0.15)',textColor:'#d29922'},
    {icon:'\u{1F6E2}\uFE0F',title:'Oil cushion',desc:'Still adequate but starting to thin',valueFrom:'buffer',color:'rgba(210,153,34,0.15)',textColor:'#d29922'},
    {icon:'\u{1F4F0}',title:'News',desc:'Reports of escalating tensions in the Gulf',value:'Concern',color:'rgba(210,153,34,0.15)',textColor:'#d29922'}]},
  mar07: { title:'The Halt', subtitle:'Hormuz traffic collapses. The market prices in catastrophe.', signals:[
    {icon:'\u{1F6A2}',title:'Hormuz traffic',desc:'Near-total collapse of visible transits',valueFrom:'hormuz',color:'rgba(248,81,73,0.15)',textColor:'#f85149'},
    {icon:'\u{1F6E2}\uFE0F',title:'Oil cushion',desc:'Below 5-year average. System is tight.',valueFrom:'buffer',color:'rgba(248,81,73,0.15)',textColor:'#f85149'},
    {icon:'\u{1F4F0}',title:'News',desc:'U.S. claims 9-10 mb/d still flowing. Trackers see ~5.',value:'Crisis',color:'rgba(248,81,73,0.15)',textColor:'#f85149'},
    {icon:'\u{1F504}',title:'Bypass routes',desc:'Yanbu and Fujairah increasing but insufficient',valueFrom:'yanbuDelta',color:'rgba(88,166,255,0.15)',textColor:'#58a6ff'}]},
  mar12: { title:'The Standstill', subtitle:'The strait is effectively closed. Prices keep climbing.', signals:[
    {icon:'\u{1F6A2}',title:'Hormuz traffic',desc:'Effectively zero visible transits',valueFrom:'hormuz',color:'rgba(248,81,73,0.15)',textColor:'#f85149'},
    {icon:'\u{1F6E2}\uFE0F',title:'Oil cushion',desc:'Critically low. Markets pricing sustained scarcity.',valueFrom:'buffer',color:'rgba(248,81,73,0.15)',textColor:'#f85149'},
    {icon:'\u{1F4F0}',title:'News',desc:'Military escort operations announced. No reopening in sight.',value:'Severe',color:'rgba(248,81,73,0.15)',textColor:'#f85149'},
    {icon:'\u{1F504}',title:'Bypass routes',desc:'Maxed out. Cannot replace Hormuz volumes.',value:'Max',color:'rgba(88,166,255,0.15)',textColor:'#58a6ff'}]},
  apr07: { title:'The Peak', subtitle:'Partial reopening begins, but the damage to price is done.', signals:[
    {icon:'\u{1F6A2}',title:'Hormuz traffic',desc:'Minimal traffic resuming. Very slow recovery.',valueFrom:'hormuz',color:'rgba(210,153,34,0.15)',textColor:'#d29922'},
    {icon:'\u{1F6E2}\uFE0F',title:'Oil cushion',desc:'Depleted. Takes months to rebuild.',valueFrom:'buffer',color:'rgba(248,81,73,0.15)',textColor:'#f85149'},
    {icon:'\u{1F4F0}',title:'News',desc:'Diplomatic talks underway. Market remains skeptical.',value:'Tense',color:'rgba(210,153,34,0.15)',textColor:'#d29922'},
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
