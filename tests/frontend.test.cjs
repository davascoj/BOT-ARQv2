const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const nodes = new Map();
function element(id) {
  if (!nodes.has(id)) nodes.set(id, {innerHTML:'', textContent:'', value:'', checked:false, open:false,
    className:'', classList:{add(){},remove(){},toggle(){}}, addEventListener(){}});
  return nodes.get(id);
}
const source = fs.readFileSync(path.join(__dirname, '../script.js'), 'utf8').split('/* ---------- Arranque')[0];
const context = vm.createContext({console, Date, Intl, Number, String, Math, Map, Set, Array,
  AbortSignal, document:{getElementById:element, addEventListener(){},hidden:false},
  fetch:async()=>{throw new Error('No network in unit tests')}, setTimeout, clearTimeout});
vm.runInContext(source, context);
let passed = 0;
function check(name, fn) { fn(); passed++; console.log('OK:',name); }
function run(code) { return vm.runInContext(code, context); }
check('null is not zero',()=>assert.equal(run('numero(null)'), '—'));
check('missing money is unavailable',()=>assert.equal(run('dinero(undefined)'), '—'));
check('real zero remains zero',()=>assert.equal(run('numero(0)'), '0'));
check('NaN rejected',()=>assert.equal(run('numero(NaN)'), '—'));
check('backend ranking preserved',()=>assert.ok(run('ordenRanking({rank:1},{rank:2})')<0));
check('legacy cannot be healthy',()=>assert.match(run('snapshotHealth({})'), /legacy/));
run(`snapshot = {schema_version:2,run_id:'test',generated_at:'2026-10-14T15:00:00Z',paper_state:{run_id:'test'},
  market_session:{market_open:'2026-10-14T13:30:00Z',market_close:'2026-10-14T20:00:00Z',next_open:'2026-10-15T13:30:00Z'},
  historial:{operaciones:[]}}`);
check('fresh coherent snapshot accepted',()=>assert.equal(run("snapshotHealth(snapshot,Date.parse('2026-10-14T15:01:00Z'))"),''));
check('stale snapshot refused',()=>assert.match(run("snapshotHealth(snapshot,Date.parse('2026-10-14T16:00:00Z'))"),/desactualizados/));
check('inconsistent run IDs refused',()=>assert.match(run("snapshotHealth({...snapshot,paper_state:{run_id:'other'}},Date.parse('2026-10-14T15:01:00Z'))"),/inconsistente/));
check('weekend snapshot not called live',()=>assert.match(run("snapshotHealth(snapshot,Date.parse('2026-10-19T15:01:00Z'))"),/desactualizados/));
run(`simulacionPro={costo_total_estimado_pct_por_operacion:0.23};
benchmarkBot={spy_rentabilidad_pct:2.24,qqq_rentabilidad_pct:-2.13}; pintarPanelProfesional();`);
check('cost field contract',()=>assert.match(element('diagnosticoBot').innerHTML,/0.23%/));
check('benchmark fields contract',()=>assert.match(element('diagnosticoBot').innerHTML,/SPY 2.24%, QQQ -2.13%/));
element('filtroEstadoHistorial').value='TODOS'; element('filtroResultadoHistorial').value='TODOS';
run(`historialOperaciones=Array.from({length:121},(_,i)=>({id:i,accion:'T'+i,estado:'CERRADA',resultado:'GANADA',pnl_usd_estimado:-1,ganancia_pct_neta_estimada:-1}));renderHistorial(2);`);
check('history includes beyond old 120-row cutoff',()=>assert.match(element('tablaHistorial').innerHTML,/T120/));
check('history summary completed',()=>assert.match(element('historialResumen').textContent,/121 conservadas/));
check('gross winning label cannot disguise net loss',()=>assert.match(element('tablaHistorial').innerHTML,/PERDIDA NETA/));
element('buscarHistorial').value='NOMATCH'; run('renderHistorial()');
check('empty filter differs from missing history',()=>assert.match(element('tablaHistorial').innerHTML,/No hay coincidencias/));
run(`historialOperaciones=[{accion:'AAA',estado:'ABIERTA',sale_locked:true,sell_eligible_at:'2026-10-15T13:30:00Z'}];renderCarteraAbierta();`);
check('overnight lock visible',()=>assert.match(element('tablaCarteraAbierta').innerHTML,/Venta bloqueada/));
const html=fs.readFileSync(path.join(__dirname,'../index.html'),'utf8');
check('heading and live status available',()=>{assert.match(html,/<h1 /);assert.match(html,/aria-live="polite"/)});
check('no percentage probability label',()=>assert.doesNotMatch(html,/>Prob\.</));
check('missing rule limit is not zero',()=>assert.match(run("barraRegla('drawdown',22,undefined)"),/límite —%/));
run("operationalRulesV44={estado:'NORMAL',drawdown_pct:22};configOperativa={simulation_config:{bloquear_entradas_drawdown_pct:35}};pintarReglasOperativasV44()");
check('drawdown threshold uses published configuration',()=>assert.match(element('operationalRulesResumen').innerHTML,/drawdown · límite 35%/));
run("paperAuditV43={summary:{},blocked_signals:[{ticker:'AAA',exposure_pct:null,open_risk_pct:null,drawdown_pct:null}]};pintarAuditoriaBloqueos()");
check('missing audit metrics are unavailable',()=>assert.equal((element('tablaBloqueos').innerHTML.match(/—%/g)||[]).length,3));
console.log(`${passed} frontend assertions passed`);

