/* ============================================================
   BOT-ARQ V4.4.5 · Dashboard
   - V4.4.3 Profesionalización visual (layout A-H, dedup, diagnóstico)
   - V4.4.4 Rendimiento (refresh 5 min, cache-busting por versión, debounce)
   No cambia el motor de análisis ni las reglas operativas V4.4.
   ============================================================ */

const APP_VERSION = "4.4.5";
const AUTO_REFRESH_MS = 5 * 60 * 1000; // 5 minutos, alineado con GitHub Actions

let datosGlobales = [];
let datosOriginales = [];
let sectorActivo = "TODOS";
let contextoMercado = null;
let configOperativa = {};
let historialOperaciones = [];
let historialResumen = {};
let metricasPro = {};
let simulacionPro = {};
let riesgoPro = {};
let equityCurve = [];
let rendimientoSectores = [];
let rendimientoMercados = [];
let mejoresOperaciones = [];
let peoresOperaciones = [];
let diagnosticoBot = {};
let benchmarkBot = {};
let paperTradingV4 = null;
let paperAuditV43 = null;
let operationalRulesV44 = null;

let renderLazyInicializado = false;
let ultimaActualizacionRender = "";
let diagEstado = { errores: [] };

/* ---------- Helpers base ---------- */
function $(id) { return document.getElementById(id); }

function safe(valor) {
  return String(valor ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function numero(valor, decimales = 2) {
  const n = Number(valor);
  if (!Number.isFinite(n)) return "—";
  return n.toFixed(decimales).replace(/\.0+$/, "");
}

function dinero(valor) {
  const n = Number(valor);
  if (!Number.isFinite(n)) return "$0";
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
}

function formatoPrecio(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString("en-US", { maximumFractionDigits: 2, minimumFractionDigits: 2 });
}

function formatoNumeroCorto(v, dec = 2) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString("en-US", { maximumFractionDigits: dec, minimumFractionDigits: dec });
}

function campo(r, claves, fallback = "") {
  for (const k of claves) {
    const v = r?.[k];
    if (v !== undefined && v !== null && String(v).trim() !== "") return v;
  }
  return fallback;
}

function claseValor(n) {
  return (Number(n || 0) >= 0) ? "valor-pos" : "valor-neg";
}

function claseScore(score) {
  const s = Number(score || 0);
  if (s >= 80) return "score-alto";
  if (s >= 60) return "score-medio";
  return "score-bajo";
}

function claseBot(bot) {
  const b = String(bot || "");
  if (b === "BUY STRONG") return "bot-buy-strong";
  if (b === "BUY") return "bot-buy";
  if (b === "HOLD") return "bot-hold";
  return "bot-sell";
}

function claseEstadoOperativo(e) {
  const s = String(e || "").toUpperCase();
  if (s === "BLOQUEADO") return "estado-bloqueado";
  if (s === "DEFENSIVO") return "estado-defensivo";
  return "estado-normal";
}

function claseProbabilidad(prob) {
  if (prob >= 84) return "prob-verde";
  if (prob >= 70) return "prob-amarillo";
  return "prob-rojo";
}

function formatoRangoEntrada(r) {
  const min = campo(r, ["Entrada min", "Entrada", "entrada_min"]);
  const max = campo(r, ["Entrada max", "entrada_max"]);
  if (min !== "" && max !== "") return `${formatoPrecio(min)} - ${formatoPrecio(max)}`;
  if (min !== "") return formatoPrecio(min);
  return "—";
}

function scoreVisual(score) {
  const s = Number(score || 0);
  const pct = Math.max(0, Math.min(100, s));
  return `
    <div class="score-visual ${claseScore(s)}">
      <span class="score-num">${formatoNumeroCorto(s, 1)}</span>
      <span class="score-track"><span class="score-fill" style="width:${pct}%"></span></span>
    </div>`;
}

function textoAccionSugerida(r) {
  const bot = String(r?.["Senal Bot"] || "");
  const riesgo = String(r?.Riesgo || "");
  if (bot === "BUY STRONG" && riesgo === "BAJO") return "Prioritaria";
  if (bot === "BUY STRONG") return "Alta prioridad";
  if (bot === "BUY") return "Vigilar entrada";
  return "No abrir";
}

/* ---------- Diagnóstico / blindaje ---------- */
function ejecutarBloqueSeguro(nombre, fn) {
  try {
    return fn();
  } catch (error) {
    console.error(`BOT-ARQ: error pintando ${nombre}`, error);
    diagEstado.errores.push(nombre);
    return null;
  }
}

function marcarCargando() {
  const el = $("loadStatus");
  if (el) { el.textContent = "Actualizando..."; el.className = "tb-load"; }
}

function actualizarLoadStatus(sinCambios) {
  const el = $("loadStatus");
  if (!el) return;
  const hora = new Date().toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" });
  if (diagEstado.errores.length) {
    el.textContent = `⚠ Error visual en: ${diagEstado.errores.join(", ")}`;
    el.className = "tb-load tb-load-err";
  } else {
    el.textContent = `✔ Datos OK · ${hora}${sinCambios ? " (sin cambios)" : ""}`;
    el.className = "tb-load tb-load-ok";
  }
}

function manejarErrorCarga(e) {
  console.error("BOT-ARQ: no se pudieron cargar datos", e);
  const el = $("loadStatus");
  if (el) { el.textContent = "⚠ Sin datos. Espera a que GitHub Actions termine."; el.className = "tb-load tb-load-err"; }
  const f = $("fecha"); if (f) f.textContent = "Sin datos";
  const mb = $("marketBox"); if (mb) mb.textContent = "Mercado: sin datos";
  const exec = $("dashboardEjecutivo");
  if (exec) exec.innerHTML = `<div class="metric-box">Sin datos cargados todavía. Ejecuta GitHub Actions o espera la próxima actualización automática.</div>`;
}

/* ---------- Carga de datos ---------- */
function bust(force) {
  const bucket = Math.floor(Date.now() / AUTO_REFRESH_MS); // estable dentro de la ventana de 5 min
  return `?v=${APP_VERSION}&t=${bucket}${force ? `&f=${Date.now()}` : ""}`;
}

async function fetchJSON(path) {
  const resp = await fetch(path);
  if (!resp.ok) throw new Error(`HTTP ${resp.status} en ${path}`);
  return await resp.json();
}

async function cargarDatos(force = false) {
  marcarCargando();
  diagEstado.errores = [];

  let data;
  try {
    data = await fetchJSON("datos_acciones.json" + bust(force));
  } catch (e) {
    manejarErrorCarga(e);
    return;
  }

  // Globals SIEMPRE actualizados (también si se omite el repintado, para las vistas lazy)
  contextoMercado = data.contexto_mercado || null;
  configOperativa = data.config_operativa || {};
  datosGlobales = data.resultados || [];
  datosOriginales = data.resultados || [];
  historialOperaciones = data.historial?.operaciones || [];
  historialResumen = data.historial?.resumen || {};
  simulacionPro = historialResumen.simulacion || {};
  riesgoPro = historialResumen.riesgo || {};
  metricasPro = historialResumen.metricas || {};
  equityCurve = historialResumen.equity_curve || [];
  benchmarkBot = historialResumen.benchmark || {};
  rendimientoSectores = historialResumen.rendimiento_por_sector || [];
  rendimientoMercados = historialResumen.rendimiento_por_mercado || [];
  mejoresOperaciones = historialResumen.mejores_operaciones || [];
  peoresOperaciones = historialResumen.peores_operaciones || [];
  diagnosticoBot = historialResumen.diagnostico_bot || {};

  await cargarPaperTradingV4(force);

  const historialFecha = $("historialFecha");
  if (historialFecha) historialFecha.textContent = "Actualizado: " + (data.historial?.actualizado || data.actualizado || "sin fecha");

  ejecutarBloqueSeguro("Barra superior", () => pintarTopbar(data));

  // Refresh inteligente: si no cambió la fecha de datos, no repintamos todo el dashboard.
  if (!force && data.actualizado && data.actualizado === ultimaActualizacionRender) {
    actualizarLoadStatus(true);
    refrescarVistasAvanzadasSiAbiertas();
    return;
  }
  ultimaActualizacionRender = data.actualizado || "";

  ejecutarBloqueSeguro("Panel ejecutivo", pintarDashboardEjecutivo);
  ejecutarBloqueSeguro("Estado del mercado", pintarMercado);
  ejecutarBloqueSeguro("Reglas operativas", pintarReglasOperativasV44);
  ejecutarBloqueSeguro("Alertas", pintarAlertasEjecutivas);
  ejecutarBloqueSeguro("Top oportunidades", renderTopOportunidades);
  ejecutarBloqueSeguro("Cartera abierta", renderCarteraAbierta);
  ejecutarBloqueSeguro("Auditoría de bloqueos", pintarAuditoriaBloqueos);
  ejecutarBloqueSeguro("Riesgo y desempeño", pintarPanelProfesional);
  ejecutarBloqueSeguro("Paper trading", pintarPaperTradingV4);
  ejecutarBloqueSeguro("Configuración técnica", pintarConfigTecnica);
  ejecutarBloqueSeguro("Render diferido", inicializarRenderDiferido);
  ejecutarBloqueSeguro("Vistas avanzadas", refrescarVistasAvanzadasSiAbiertas);

  actualizarLoadStatus(false);
}

function actualizarManual() { cargarDatos(true); }

async function cargarPaperTradingV4(force = false) {
  try {
    paperTradingV4 = await fetchJSON("paper/paper_state.json" + bust(force));
    paperAuditV43 = paperTradingV4.audit || null;
    operationalRulesV44 = paperTradingV4.operational_rules || paperTradingV4.risk?.operational_rules || null;
  } catch (e) {
    console.warn("BOT-ARQ: paper_state.json no disponible (el resto del dashboard sigue).", e);
    paperTradingV4 = null;
    paperAuditV43 = null;
    operationalRulesV44 = null;
  }
}

/* ---------- A. Barra superior ---------- */
function pintarTopbar(data) {
  const v = $("tbVersion"); if (v) v.textContent = "V" + APP_VERSION;
  const f = $("fecha"); if (f) f.textContent = "Actualizado: " + (data.actualizado || "—");
  const broker = !!paperTradingV4?.status?.broker_real_enabled;
  const b = $("tbBroker");
  if (b) { b.textContent = broker ? "BROKER REAL ON" : "BROKER REAL OFF"; b.classList.toggle("tb-broker-on", broker); }
}

/* ---------- B. Panel ejecutivo ---------- */
function pintarDashboardEjecutivo() {
  const box = $("dashboardEjecutivo");
  if (!box) return;
  const sim = simulacionPro || {};
  const riesgo = riesgoPro || {};
  const paperPortfolio = paperTradingV4?.portfolio || {};
  const estadoOp = operationalRulesV44?.estado || paperTradingV4?.status?.operational_mode || "NORMAL";

  box.innerHTML = `
    <div class="metric-box">
      <strong>${dinero(sim.capital_actual_total_estimado ?? paperPortfolio.capital_initial_usd ?? 0)}</strong>
      <span>capital total estimado</span>
    </div>
    <div class="metric-box">
      <strong class="${claseValor(sim.ganancia_total_estimada_usd ?? paperPortfolio.total_pnl_usd_estimated)}">${dinero(sim.ganancia_total_estimada_usd ?? paperPortfolio.total_pnl_usd_estimated ?? 0)}</strong>
      <span>G/P total estimada</span>
    </div>
    <div class="metric-box">
      <strong>${riesgo.operaciones_abiertas ?? paperTradingV4?.status?.positions_open ?? 0}/${riesgo.max_operaciones_abiertas ?? "—"}</strong>
      <span>operaciones abiertas</span>
    </div>
    <div class="metric-box">
      <strong>${numero(riesgo.exposicion_abierta_pct ?? paperPortfolio.exposure_pct ?? 0)}%</strong>
      <span>exposición abierta / capital inicial</span>
    </div>
    <div class="metric-box">
      <strong>${numero(riesgo.riesgo_total_abierto_pct ?? paperPortfolio.open_risk_pct ?? 0)}%</strong>
      <span>riesgo abierto / capital inicial</span>
    </div>
    <div class="metric-box">
      <strong class="estado-pill ${claseEstadoOperativo(estadoOp)}">${safe(estadoOp)}</strong>
      <span>estado operativo</span>
    </div>`;
}

/* ---------- C. Estado del mercado ---------- */
function pintarMercado() {
  const marketBox = $("marketBox");
  const badge = $("marketBadge");
  const grid = $("marketGrid");

  if (!contextoMercado) {
    if (marketBox) { marketBox.textContent = "Mercado: sin datos"; }
    if (badge) badge.textContent = "—";
    if (grid) grid.innerHTML = `<div class="metric-box">Sin datos de mercado todavía.</div>`;
    return;
  }

  const estado = contextoMercado.estado || "NEUTRO";
  const spy = Number(contextoMercado.spy20 ?? 0);
  const qqq = Number(contextoMercado.qqq20 ?? 0);
  const score = contextoMercado.score ?? "—";

  if (marketBox) marketBox.textContent = `Tendencia general: ${estado}`;
  if (badge) {
    badge.textContent = estado;
    badge.className = "mode-badge " + estado.toLowerCase().replaceAll(" ", "-").replace("é", "e").replace("+", "plus");
  }
  if (grid) {
    grid.innerHTML = `
      <div class="metric-box"><strong>${safe(estado)}</strong><span>tendencia / modo</span></div>
      <div class="metric-box"><strong class="${claseValor(spy)}">${numero(spy)}%</strong><span>SPY 20D</span></div>
      <div class="metric-box"><strong class="${claseValor(qqq)}">${numero(qqq)}%</strong><span>QQQ 20D</span></div>
      <div class="metric-box"><strong>${safe(score)}</strong><span>score de mercado</span></div>`;
  }
}

/* ---------- D. Reglas operativas V4.4 ---------- */
function barraRegla(label, actual, limite, sufijo = "%") {
  const a = Number(actual) || 0;
  const lim = Number(limite) || 0;
  const pct = lim > 0 ? Math.max(0, Math.min(100, (a / lim) * 100)) : 0;
  const cls = pct >= 100 ? "rf-danger" : (pct >= 70 ? "rf-warn" : "rf-ok");
  return `
    <div class="metric-box rule-metric">
      <strong>${numero(a)}${sufijo}</strong>
      <span>${label} · límite ${numero(lim)}${sufijo}</span>
      <span class="rule-bar"><span class="rule-fill ${cls}" style="width:${pct}%"></span></span>
    </div>`;
}

function pintarReglasOperativasV44() {
  const box = $("operationalRulesResumen");
  const badge = $("operationalRulesBadge");
  const motivoBox = $("operationalRulesMotivo");
  if (!box) return;

  if (!operationalRulesV44) {
    box.innerHTML = `<div class="metric-box">Reglas operativas pendientes. Se llenarán en la próxima ejecución del bot.</div>`;
    if (badge) { badge.textContent = "Pendiente"; badge.className = "mode-badge v4-badge warning"; }
    if (motivoBox) motivoBox.textContent = "";
    return;
  }

  const r = operationalRulesV44;
  const estado = r.estado || "NORMAL";
  if (badge) { badge.textContent = estado; badge.className = "mode-badge v4-badge " + claseEstadoOperativo(estado); }

  box.innerHTML =
    `<div class="metric-box"><strong class="estado-pill ${claseEstadoOperativo(estado)}">${safe(estado)}</strong><span>estado operativo</span></div>` +
    barraRegla("exposición abierta", r.exposicion_abierta_pct, r.max_exposicion_total_pct) +
    barraRegla("riesgo abierto", r.riesgo_abierto_pct, r.max_riesgo_total_abierto_pct) +
    barraRegla("drawdown", r.drawdown_pct, r.bloquear_entradas_drawdown_pct) +
    `<div class="metric-box"><strong>${safe(r.bloqueos_generados ?? 0)}</strong><span>bloqueos generados</span></div>`;

  if (motivoBox) {
    motivoBox.innerHTML = `<strong>Motivo principal:</strong> ${safe(r.motivo_principal || "Sin bloqueos")}`;
  }
}

/* ---------- Alertas operativas ---------- */
function pintarAlertasEjecutivas() {
  const box = $("alertasEjecutivas");
  if (!box) return;

  const alertas = [];
  const riesgo = riesgoPro || {};
  const diag = diagnosticoBot || {};
  const paperWarnings = paperTradingV4?.status?.warnings || [];

  paperWarnings.forEach(w => alertas.push({ tipo: "warning", texto: w }));

  const exp = Number(riesgo.exposicion_abierta_pct ?? 0);
  const risk = Number(riesgo.riesgo_total_abierto_pct ?? 0);
  const dd = Number(riesgo.max_drawdown_pct ?? 0);
  const abiertas = Number(riesgo.operaciones_abiertas ?? 0);
  const maxAbiertas = Number(riesgo.max_operaciones_abiertas ?? 0);

  if (maxAbiertas && abiertas >= maxAbiertas) alertas.push({ tipo: "danger", texto: "Máximo de operaciones abiertas alcanzado." });
  if (exp > 80) alertas.push({ tipo: "danger", texto: `Exposición abierta alta: ${numero(exp)}%.` });
  if (risk > 10) alertas.push({ tipo: "danger", texto: `Riesgo abierto elevado: ${numero(risk)}%.` });
  if (dd > 20) alertas.push({ tipo: "warning", texto: `Drawdown histórico relevante: -${numero(dd)}%.` });

  if (Array.isArray(diag.alertas)) diag.alertas.slice(0, 4).forEach(a => alertas.push({ tipo: "info", texto: a }));

  if (!alertas.length) {
    box.innerHTML = `<div class="alert-item ok">Sin alertas críticas. Mantener monitoreo normal.</div>`;
    return;
  }

  const vistos = new Set();
  const unicas = [];
  alertas.forEach(a => {
    const key = String(a.texto || "").trim();
    if (key && !vistos.has(key)) { vistos.add(key); unicas.push(a); }
  });

  box.innerHTML = unicas.slice(0, 8).map(a => `<div class="alert-item ${a.tipo}">${safe(a.texto)}</div>`).join("");
}

/* ---------- E. Top oportunidades ---------- */
function renderTopOportunidades() {
  const tbody = $("tablaTopOportunidades");
  if (!tbody) return;

  let datos = [...datosOriginales].filter(r =>
    ["BUY STRONG", "BUY"].includes(String(r["Senal Bot"] || "")) &&
    ["BAJO", "MEDIO"].includes(String(r.Riesgo || ""))
  );
  datos.sort(ordenRanking);
  datos = datos.slice(0, 10);

  if (!datos.length) {
    tbody.innerHTML = `<tr><td colspan="11">No hay oportunidades BUY con riesgo bajo/medio en este momento.</td></tr>`;
    return;
  }

  tbody.innerHTML = datos.map(r => {
    const precio = campo(r, ["Precio actual", "Precio"]);
    const stop = campo(r, ["Stop loss", "Stop"]);
    const objetivo = campo(r, ["Objetivo"]);
    const score = campo(r, ["Score calidad", "Score"], 0);
    const rr = campo(r, ["R/R", "rr"]);
    const bot = String(r["Senal Bot"] || "");
    return `
      <tr>
        <td class="ticker-cell"><strong>${safe(r.Accion)}</strong></td>
        <td>${safe(r.Sector)}</td>
        <td class="num">${formatoPrecio(precio)}</td>
        <td><span class="bot-badge ${claseBot(bot)}">${safe(bot)}</span><small class="subsignal">${safe(r.Senal || "")}</small></td>
        <td>${scoreVisual(score)}</td>
        <td><span class="badge ${String(r.Riesgo || "").toLowerCase()}">${safe(r.Riesgo)}</span></td>
        <td class="entry-range">${formatoRangoEntrada(r)}</td>
        <td class="num">${formatoPrecio(stop)}</td>
        <td class="num objetivo-cell">${formatoPrecio(objetivo)}</td>
        <td class="num">${rr === "" ? "—" : numero(rr, 2)}</td>
        <td><span class="action-chip">${safe(textoAccionSugerida(r))}</span></td>
      </tr>`;
  }).join("");
}

/* ---------- F. Cartera abierta ---------- */
function renderCarteraAbierta() {
  const tbody = $("tablaCarteraAbierta");
  if (!tbody) return;
  const abiertas = historialOperaciones
    .filter(op => String(op.estado || "") === "ABIERTA")
    .sort((a, b) => Number(b.score_calidad_actual || 0) - Number(a.score_calidad_actual || 0));

  if (!abiertas.length) {
    tbody.innerHTML = `<tr><td colspan="10">No hay operaciones abiertas actualmente.</td></tr>`;
    return;
  }

  tbody.innerHTML = abiertas.slice(0, 40).map(op => {
    const gananciaPct = Number(op.ganancia_pct ?? 0);
    const gpUsd = op.ganancia_abierta_usd_estimada ?? op.pnl_usd_estimado ?? 0;
    const botActual = op.senal_bot_actual || op.senal_bot_entrada || "";
    return `<tr>
      <td class="ticker-cell"><strong>${safe(op.accion)}</strong></td>
      <td>${safe(op.sector || "Otro")}</td>
      <td class="num">${formatoPrecio(op.precio_entrada)}</td>
      <td class="num">${formatoPrecio(op.precio_actual)}</td>
      <td class="num ${claseValor(gpUsd)}">${dinero(gpUsd)}</td>
      <td class="num ${gananciaPct >= 0 ? "hist-pos" : "hist-neg"}">${numero(gananciaPct)}%</td>
      <td class="num">${formatoPrecio(op.stop)}</td>
      <td class="num objetivo-cell">${formatoPrecio(op.objetivo)}</td>
      <td class="num valor-neg">${dinero(op.riesgo_usd_estimado ?? op.perdida_maxima_stop_usd ?? 0)}</td>
      <td><span class="bot-badge ${claseBot(botActual)}">${safe(botActual)}</span></td>
    </tr>`;
  }).join("");
}

/* ---------- G. Auditoría de bloqueos ---------- */
function pintarAuditoriaBloqueos() {
  const summary = $("auditSummary");
  const tbody = $("tablaBloqueos");
  const badge = $("auditBadge");
  if (!summary || !tbody) return;

  if (!paperAuditV43) {
    summary.innerHTML = `<div class="metric-box">Auditoría pendiente. Se llenará en la próxima ejecución del bot.</div>`;
    tbody.innerHTML = `<tr><td colspan="8">Sin auditoría disponible todavía.</td></tr>`;
    if (badge) badge.textContent = "Pendiente";
    return;
  }

  const s = paperAuditV43.summary || {};
  const blocked = paperAuditV43.blocked_signals || [];
  if (badge) badge.textContent = `${s.blocked_count || 0} bloqueadas`;

  summary.innerHTML = `
    <div class="metric-box"><strong>${s.blocked_count || 0}</strong><span>señales bloqueadas</span></div>
    <div class="metric-box"><strong>${s.buy_candidates_count || 0}</strong><span>candidatas BUY</span></div>
    <div class="metric-box"><strong>${s.open_positions_count || 0}</strong><span>posiciones abiertas</span></div>
    <div class="metric-box"><strong>${safe(s.main_block_reason || "Sin bloqueos")}</strong><span>motivo principal</span></div>`;

  if (!blocked.length) {
    tbody.innerHTML = `<tr><td colspan="8">No hay señales bloqueadas registradas.</td></tr>`;
    return;
  }

  tbody.innerHTML = blocked.slice(0, 15).map(b => `
    <tr>
      <td class="ticker-cell"><strong>${safe(b.ticker)}</strong></td>
      <td><span class="bot-badge ${claseBot(b.signal)}">${safe(b.signal)}</span></td>
      <td>${safe(b.reason)}</td>
      <td><span class="score-pill ${claseScore(b.score)}">${numero(b.score ?? 0, 1)}</span></td>
      <td>${b.operational_rule ? '<span class="op-rule-dot">OP</span>' : '<span class="mini-copy">—</span>'}</td>
      <td class="num">${numero(b.exposure_pct ?? 0)}%</td>
      <td class="num">${numero(b.open_risk_pct ?? 0)}%</td>
      <td class="num">${numero(b.drawdown_pct ?? 0)}%</td>
    </tr>`).join("");
}

/* ---------- Riesgo y desempeño (compacto, sin duplicar el panel ejecutivo) ---------- */
function pintarPanelProfesional() {
  const sim = simulacionPro || {};
  const riesgo = riesgoPro || {};
  const met = metricasPro || {};
  const diag = diagnosticoBot || {};
  const hr = historialResumen || {};

  const resumen = $("simulacionResumen");
  if (resumen) {
    resumen.innerHTML = `
      <div class="metric-box"><strong>${dinero(sim.capital_inicial ?? 0)}</strong><span>capital inicial</span></div>
      <div class="metric-box"><strong>${numero(met.profit_factor ?? 0)}</strong><span>profit factor</span></div>
      <div class="metric-box"><strong>${numero(hr.win_rate ?? 0)}%</strong><span>win rate (cerradas)</span></div>
      <div class="metric-box"><strong>${hr.cerradas ?? 0}</strong><span>operaciones cerradas</span></div>
      <div class="metric-box"><strong class="valor-neg">-${numero(riesgo.max_drawdown_pct ?? 0)}%</strong><span>máx. drawdown</span></div>
      <div class="metric-box"><strong>${numero(met.expectativa_pct_por_operacion ?? 0)}%</strong><span>expectativa / operación</span></div>`;
  }

  const riesgoCaja = $("riesgoResumen");
  if (riesgoCaja) {
    riesgoCaja.innerHTML = `
      <div><strong>${riesgo.racha_max_perdidas ?? 0}</strong><span>racha pérdidas</span></div>
      <div><strong>${riesgo.operaciones_abiertas ?? 0}/${riesgo.max_operaciones_abiertas ?? 0}</strong><span>operaciones abiertas</span></div>
      <div><strong>${numero(riesgo.exposicion_abierta_pct ?? 0)}%</strong><span>exposición</span></div>
      <div><strong>${numero(riesgo.riesgo_total_abierto_pct ?? 0)}%</strong><span>riesgo abierto</span></div>
      <div><strong>${dinero(riesgo.riesgo_total_abierto_usd ?? 0)}</strong><span>riesgo USD</span></div>
      <div><strong class="${claseValor(benchmarkBot.bot_vs_spy_alpha_pct)}">${numero(benchmarkBot.bot_vs_spy_alpha_pct ?? 0)}%</strong><span>bot vs SPY</span></div>`;
  }

  const diagCaja = $("diagnosticoBot");
  if (diagCaja) {
    const modo = String(diag.modo || "SIMULACIÓN");
    const riesgoSistema = String(diag.riesgo_sistema || "SIN DATOS");
    const alertas = Array.isArray(diag.alertas) && diag.alertas.length ? diag.alertas : ["Sin alertas críticas registradas."];
    diagCaja.innerHTML = `
      <div class="diagnostico-head">
        <span class="diag-mode ${modo.toLowerCase()}">${safe(modo)}</span>
        <span class="diag-risk ${riesgoSistema.toLowerCase()}">Riesgo ${safe(riesgoSistema)}</span>
      </div>
      <p>${safe(diag.mensaje || "Sistema en seguimiento paper trading.")}</p>
      <ul>${alertas.slice(0, 5).map(a => `<li>${safe(a)}</li>`).join("")}</ul>
      <p class="mini-copy">Costo estimado/op: ${numero(met.costo_total_pct_estimado ?? 0)}%. Benchmark: SPY ${numero(benchmarkBot.spy_pct ?? 0)}%, QQQ ${numero(benchmarkBot.qqq_pct ?? 0)}%.</p>`;
  }
}

/* ---------- H. Paper Trading Engine (avanzado) ---------- */
function pintarPaperTradingV4() {
  const box = $("paperV4Resumen");
  const health = $("paperV4Health");
  const warnings = $("paperV4Warnings");
  if (!box) return;

  if (!paperTradingV4 || !paperTradingV4.status) {
    box.innerHTML = `<div class="metric-box">Motor V4 pendiente. Espera la próxima ejecución de GitHub Actions.</div>`;
    if (health) { health.textContent = "V4 pendiente"; health.className = "mode-badge v4-badge warning"; }
    if (warnings) warnings.innerHTML = "";
    return;
  }

  const status = paperTradingV4.status || {};
  const portfolio = paperTradingV4.portfolio || {};
  const risk = paperTradingV4.risk || {};
  const warningList = status.warnings || [];

  if (health) {
    health.textContent = `${status.health || "OK"} · ${status.mode || "PAPER"}`;
    health.className = "mode-badge v4-badge " + ((status.health || "OK") === "OK" ? "ok" : "warning");
  }

  box.innerHTML = `
    <div class="metric-box"><strong>${safe(status.positions_open ?? 0)}</strong><span>posiciones paper abiertas</span></div>
    <div class="metric-box"><strong>${safe(status.orders_total ?? 0)}</strong><span>órdenes simuladas</span></div>
    <div class="metric-box"><strong>${safe(status.trades_closed ?? 0)}</strong><span>trades cerrados</span></div>
    <div class="metric-box"><strong>${dinero(portfolio.exposure_usd ?? 0)}</strong><span>exposición paper</span></div>
    <div class="metric-box"><strong>${dinero(portfolio.open_risk_usd ?? 0)}</strong><span>riesgo abierto paper</span></div>
    <div class="metric-box"><strong class="${claseValor(portfolio.total_pnl_usd_estimated)}">${dinero(portfolio.total_pnl_usd_estimated ?? 0)}</strong><span>G/P total estimada</span></div>
    <div class="metric-box"><strong>${numero(risk.remaining_position_slots ?? 0, 0)}</strong><span>cupos disponibles</span></div>
    <div class="metric-box"><strong>${safe(status.broker_real_enabled ? "ON" : "OFF")}</strong><span>broker real</span></div>`;

  if (warnings) {
    warnings.innerHTML = warningList.length
      ? `<strong>Alertas V4:</strong><ul>${warningList.map(w => `<li>${safe(w)}</li>`).join("")}</ul>`
      : `<span class="paper-ok">Sin alertas críticas del motor V4.</span>`;
  }
}

/* ---------- Configuración técnica (avanzado) ---------- */
function pintarConfigTecnica() {
  const tbody = $("tablaConfigTecnica");
  if (!tbody) return;
  const cfg = (configOperativa && configOperativa.simulation_config) || {};
  const labels = {
    capital_inicial: "Capital inicial (USD)",
    riesgo_por_operacion_pct: "Riesgo por operación %",
    max_posicion_pct: "Máx. posición %",
    max_operaciones_abiertas: "Máx. operaciones abiertas",
    max_exposicion_total_pct: "Máx. exposición total %",
    max_riesgo_total_abierto_pct: "Máx. riesgo abierto %",
    modo_defensivo_drawdown_pct: "Modo defensivo · drawdown %",
    bloquear_entradas_drawdown_pct: "Bloqueo de entradas · drawdown %",
    rr_minimo: "R/R mínimo",
    volumen_relativo_minimo: "Volumen relativo mínimo",
    comision_por_operacion_pct: "Comisión por operación %",
    slippage_pct: "Slippage %",
    spread_pct: "Spread %"
  };
  const filas = Object.keys(labels)
    .filter(k => cfg[k] !== undefined)
    .map(k => `<tr><td>${labels[k]}</td><td class="num">${safe(cfg[k])}</td></tr>`);

  tbody.innerHTML = filas.length
    ? filas.join("")
    : `<tr><td colspan="2">Configuración no disponible en datos_acciones.json todavía.</td></tr>`;
}

/* ---------- Curva de capital ---------- */
function dibujarEquityCurve() {
  const canvas = $("equityChart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const w = canvas.width, h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#0f172a";
  ctx.fillRect(0, 0, w, h);

  const puntos = Array.isArray(equityCurve) ? equityCurve : [];
  if (puntos.length < 2) {
    ctx.fillStyle = "#cbd5e1";
    ctx.font = "18px Arial";
    ctx.fillText("Aún no hay suficientes operaciones cerradas para dibujar la curva de capital.", 30, 60);
    return;
  }

  const margen = 42;
  const valores = puntos.map(p => Number(p.capital || 0)).filter(Number.isFinite);
  const min = Math.min(...valores), max = Math.max(...valores);
  const rango = Math.max(max - min, 1);

  ctx.strokeStyle = "#334155";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = margen + ((h - margen * 2) * i / 4);
    ctx.beginPath(); ctx.moveTo(margen, y); ctx.lineTo(w - margen, y); ctx.stroke();
  }

  ctx.strokeStyle = "#38bdf8";
  ctx.lineWidth = 3;
  ctx.beginPath();
  puntos.forEach((p, i) => {
    const x = margen + ((w - margen * 2) * i / (puntos.length - 1));
    const y = h - margen - (((Number(p.capital || 0) - min) / rango) * (h - margen * 2));
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.stroke();

  ctx.fillStyle = "#e2e8f0";
  ctx.font = "13px Arial";
  ctx.fillText(`Máx: ${dinero(max)}`, margen, 22);
  ctx.fillText(`Mín: ${dinero(min)}`, margen, h - 12);
  const ultimo = puntos[puntos.length - 1];
  ctx.fillText(`Actual cerrado: ${dinero(ultimo.capital || 0)}`, w - 245, 22);
}

/* ---------- Tablas avanzadas (sector/mercado/mejores/peores) ---------- */
function llenarTablaSimple(id, filas, tipo) {
  const tbody = $(id);
  if (!tbody) return;
  if (!Array.isArray(filas) || filas.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5">Sin datos todavía.</td></tr>`;
    return;
  }
  tbody.innerHTML = filas.slice(0, 10).map(f => {
    if (tipo === "grupo") {
      return `<tr>
        <td><strong>${safe(f.grupo)}</strong></td>
        <td>${safe(f.operaciones)}</td>
        <td>${numero(f.win_rate ?? 0)}%</td>
        <td class="${claseValor(f.rentabilidad_neta_pct)}">${numero(f.rentabilidad_neta_pct ?? 0)}%</td>
        <td>${f.profit_factor === null || f.profit_factor === undefined ? "∞" : numero(f.profit_factor)}</td>
      </tr>`;
    }
    return `<tr>
      <td><strong>${safe(f.accion)}</strong></td>
      <td class="${claseValor(f.ganancia_pct_final)}">${numero(f.ganancia_pct_final ?? 0)}%</td>
      <td class="${claseValor(f.pnl_usd_estimado)}">${dinero(f.pnl_usd_estimado ?? 0)}</td>
      <td>${safe(f.tipo_cierre || f.resultado || "")}</td>
    </tr>`;
  }).join("");
}

function renderTablasAvanzadas() {
  llenarTablaSimple("tablaSectores", rendimientoSectores, "grupo");
  llenarTablaSimple("tablaMercados", rendimientoMercados, "grupo");
  llenarTablaSimple("tablaMejores", mejoresOperaciones, "ops");
  llenarTablaSimple("tablaPeores", peoresOperaciones, "ops");
}

/* ---------- Ranking completo ---------- */
function prioridadSenal(senal) {
  if (senal === "COMPRA FUERTE") return 3;
  if (senal === "POSIBLE COMPRA") return 2;
  if (senal === "VIGILAR") return 1;
  return 0;
}
function prioridadRiesgo(riesgo) {
  if (riesgo === "BAJO") return 2;
  if (riesgo === "MEDIO") return 1;
  return 0;
}
function ordenRanking(a, b) {
  const aHot = String(a["Hot Score"] || "").length;
  const bHot = String(b["Hot Score"] || "").length;
  return (
    prioridadSenal(b.Senal) - prioridadSenal(a.Senal) ||
    prioridadRiesgo(b.Riesgo) - prioridadRiesgo(a.Riesgo) ||
    bHot - aHot ||
    Number(b["Probabilidad tecnica"] || 0) - Number(a["Probabilidad tecnica"] || 0) ||
    Number(b["Fuerza relativa"] || 0) - Number(a["Fuerza relativa"] || 0) ||
    Number(a["ATR %"] || 99) - Number(b["ATR %"] || 99)
  );
}

function renderTabla() {
  const tabla = $("tabla");
  if (!tabla) return;
  const soloCompra = $("soloCompra")?.checked || false;
  const soloHot = $("soloHot")?.checked || false;
  const ocultarAlto = $("ocultarAlto")?.checked || false;
  const busqueda = $("buscarAccion")?.value.trim().toUpperCase() || "";

  let datos = [...datosGlobales];
  if (sectorActivo !== "TODOS") datos = datos.filter(r => String(r.Sector || "").includes(sectorActivo));
  if (busqueda !== "") datos = datos.filter(r => String(r.Accion || "").toUpperCase().includes(busqueda));
  if (soloCompra) datos = datos.filter(r => ["BUY STRONG", "BUY"].includes(String(r["Senal Bot"] || "")));
  if (soloHot) datos = datos.filter(r => String(r["Hot Score"] || "").includes("🔥"));
  if (ocultarAlto) datos = datos.filter(r => String(r.Riesgo || "") !== "ALTO");

  datos.sort(ordenRanking);

  if (datos.length === 0) {
    tabla.innerHTML = `<tr><td colspan="20">No hay resultados con esos filtros.</td></tr>`;
    return;
  }

  tabla.innerHTML = datos.map(r => {
    const riesgo = String(r.Riesgo || "").toLowerCase();
    const senal = String(r.Senal || "");
    const bot = String(r["Senal Bot"] || "");
    const prob = Number(r["Probabilidad tecnica"] || 0);
    const momentum = Number(r.Momentum || 0);
    const fuerzaRel = Number(r["Fuerza relativa"] || 0);

    let claseSenal = "no";
    if (senal === "COMPRA FUERTE") claseSenal = "fuerte";
    else if (senal.includes("POSIBLE")) claseSenal = "compra";
    else if (senal.includes("VIGILAR")) claseSenal = "vigilar";

    const claseMom = momentum >= 0 ? "mom-pos" : "mom-neg";
    const claseRel = fuerzaRel >= 0 ? "mom-pos" : "mom-neg";
    const detalle = [r.Razones, r.Alertas].filter(Boolean).join(" | ");

    return `<tr>
      <td><strong>${safe(r.Accion)}</strong></td>
      <td>${safe(r.Sector || "Otro")}</td>
      <td class="num">${formatoPrecio(campo(r, ["Precio actual", "Precio"]))}</td>
      <td class="num"><span class="prob ${claseProbabilidad(prob)}">${numero(prob, 1)}%</span></td>
      <td class="num ${claseMom}">${numero(momentum)}%</td>
      <td class="num ${claseRel}">${numero(fuerzaRel)}%</td>
      <td>${safe(r["Hot Score"] || "")}</td>
      <td><span class="conf ${String(r.Confirmacion || "MEDIA").toLowerCase()}">${safe(r.Confirmacion || "MEDIA")}</span></td>
      <td class="num">${numero(r["ATR %"] ?? 0)}%</td>
      <td class="num entry-range">${formatoRangoEntrada(r)}</td>
      <td class="num">${formatoPrecio(campo(r, ["Stop loss", "Stop"]))}</td>
      <td class="num objetivo-cell">${formatoPrecio(r.Objetivo)}</td>
      <td class="num">${r["R/R"] ? numero(r["R/R"], 2) : "—"}</td>
      <td class="num">${numero(r.RSI, 1)}</td>
      <td>${safe(r.Mercado || "NEUTRO")}</td>
      <td><span class="badge ${riesgo}">${safe(r.Riesgo)}</span></td>
      <td class="${claseSenal}">${safe(r.Senal)}</td>
      <td><span class="score-pill ${claseScore(r["Score calidad"])}">${numero(r["Score calidad"] ?? 0, 1)}</span></td>
      <td><span class="bot-badge ${claseBot(bot)}">${safe(bot)}</span></td>
      <td class="detalle" title="${safe(detalle)}">${safe(detalle || "-")}</td>
    </tr>`;
  }).join("");
}

/* ---------- Historial ---------- */
function renderHistorial() {
  const tabla = $("tablaHistorial");
  if (!tabla) return;

  const busqueda = $("buscarHistorial")?.value.trim().toUpperCase() || "";
  const estadoFiltro = $("filtroEstadoHistorial")?.value || "TODOS";
  const resultadoFiltro = $("filtroResultadoHistorial")?.value || "TODOS";

  let ops = [...historialOperaciones];
  if (estadoFiltro !== "TODOS") ops = ops.filter(op => String(op.estado || "") === estadoFiltro);
  if (resultadoFiltro !== "TODOS") ops = ops.filter(op => String(op.resultado || "").startsWith(resultadoFiltro));
  if (busqueda) {
    ops = ops.filter(op =>
      String(op.accion || "").toUpperCase().includes(busqueda) ||
      String(op.resultado || "").toUpperCase().includes(busqueda) ||
      String(op.tipo_cierre || "").toUpperCase().includes(busqueda)
    );
  }

  if (ops.length === 0) {
    tabla.innerHTML = `<tr><td colspan="15">Todavía no hay historial. Ejecuta el análisis una vez y la app empezará a guardar señales.</td></tr>`;
    return;
  }

  tabla.innerHTML = ops.slice(0, 120).map(op => {
    const estado = String(op.estado || "");
    const ganancia = Number(op.estado === "CERRADA" ? (op.ganancia_pct_final ?? op.ganancia_pct ?? 0) : (op.ganancia_pct ?? 0));
    const claseGanancia = ganancia >= 0 ? "hist-pos" : "hist-neg";
    const claseEstado = estado === "ABIERTA" ? "hist-open" : "hist-closed";
    const botActual = op.senal_bot_actual || op.senal_bot_entrada || "";
    const gpUsd = op.estado === "ABIERTA" ? (op.ganancia_abierta_usd_estimada ?? op.pnl_usd_estimado ?? 0) : (op.pnl_usd_estimado ?? 0);
    return `<tr>
      <td><span class="hist-status ${claseEstado}">${safe(estado)}</span></td>
      <td><strong>${safe(op.accion)}</strong></td>
      <td class="num">${formatoPrecio(op.precio_entrada)}</td>
      <td class="num">${formatoPrecio(op.precio_actual ?? op.precio_cierre)}</td>
      <td class="num ${claseGanancia}">${numero(ganancia)}%</td>
      <td class="num ${claseValor(gpUsd)}">${dinero(gpUsd)}</td>
      <td class="num">${dinero(op.riesgo_usd_estimado ?? 0)}</td>
      <td class="num">${formatoPrecio(op.stop)}</td>
      <td class="num objetivo-cell">${formatoPrecio(op.objetivo)}</td>
      <td class="num">${op.rr ? numero(op.rr, 2) : "—"}</td>
      <td>${safe(op.fecha_entrada)}</td>
      <td class="num">${safe(op.dias_abierta ?? 0)}</td>
      <td>${safe(op.senal_entrada)}</td>
      <td><span class="bot-badge ${claseBot(botActual)}">${safe(botActual)}</span></td>
      <td>${safe(op.resultado || "EN SEGUIMIENTO")}</td>
    </tr>`;
  }).join("");
}

/* ---------- Filtros / acciones ---------- */
function filtrarSector(sector) {
  datosGlobales = [...datosOriginales];
  sectorActivo = sector;
  const ranking = $("rankingCompletoDetails");
  if (ranking) ranking.open = true;
  renderTabla();
}

function limpiarBusqueda() {
  const buscar = $("buscarAccion");
  if (buscar) buscar.value = "";
  datosGlobales = [...datosOriginales];
  sectorActivo = "TODOS";
  ["soloCompra", "soloHot", "ocultarAlto"].forEach(id => { const el = $(id); if (el) el.checked = false; });
  const ranking = $("rankingCompletoDetails");
  if (ranking) ranking.open = true;
  renderTabla();
}

function mostrarTop4() {
  let datos = [...datosOriginales].filter(r =>
    ["BUY STRONG", "BUY"].includes(String(r["Senal Bot"] || "")) &&
    ["BAJO", "MEDIO"].includes(r.Riesgo)
  );
  datos.sort(ordenRanking);
  datosGlobales = datos.slice(0, 4);
  sectorActivo = "TODOS";
  const buscar = $("buscarAccion"); if (buscar) buscar.value = "";
  ["soloCompra", "soloHot", "ocultarAlto"].forEach(id => { const el = $(id); if (el) el.checked = false; });
  const ranking = $("rankingCompletoDetails");
  if (ranking) { ranking.open = true; ranking.scrollIntoView({ behavior: "smooth", block: "start" }); }
  renderTabla();
}

function scrollHistorial() {
  const card = $("historialCard");
  if (card) {
    card.open = true;
    renderHistorial();
    card.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function ejecutarAnalisis() {
  const usuario = "davascoj";
  const repoDetectado = location.pathname.split("/").filter(Boolean)[0];
  const repo = repoDetectado || "BOT-ARQv2";
  const url = `https://github.com/${usuario}/${repo}/actions/workflows/analizar.yml`;
  window.open(url, "_blank");
}

/* ---------- Debounce de búsquedas (function declarations para handlers inline) ---------- */
let _tBuscarRanking, _tBuscarHist;
function buscarRankingDebounced() { clearTimeout(_tBuscarRanking); _tBuscarRanking = setTimeout(renderTabla, 250); }
function buscarHistorialDebounced() { clearTimeout(_tBuscarHist); _tBuscarHist = setTimeout(renderHistorial, 250); }

/* ---------- Render diferido (lazy) ---------- */
function inicializarRenderDiferido() {
  if (renderLazyInicializado) return;
  renderLazyInicializado = true;

  const wire = (id, fn) => {
    const el = $(id);
    if (el) el.addEventListener("toggle", () => { if (el.open) fn(); });
  };
  wire("rankingCompletoDetails", renderTabla);
  wire("historialCard", renderHistorial);
  wire("metricasAvanzadasDetails", renderTablasAvanzadas);
  wire("equityDetails", dibujarEquityCurve);
  wire("paperEngineDetails", pintarPaperTradingV4);
}

function refrescarVistasAvanzadasSiAbiertas() {
  if ($("rankingCompletoDetails")?.open) renderTabla();
  else { const t = $("tabla"); if (t) t.innerHTML = `<tr><td colspan="20">Abra esta sección para cargar el ranking completo (mejora la velocidad).</td></tr>`; }

  if ($("historialCard")?.open) renderHistorial();
  else { const t = $("tablaHistorial"); if (t) t.innerHTML = `<tr><td colspan="15">Abra esta sección para cargar el historial completo.</td></tr>`; }

  if ($("metricasAvanzadasDetails")?.open) renderTablasAvanzadas();
  if ($("equityDetails")?.open) dibujarEquityCurve();
}

/* ============================================================
   AVISO VISUAL DE ESTADO DEL SISTEMA (reloj NYSE)
   Lunes a viernes, 9:30 a.m. a 4:00 p.m. New York.
   ============================================================ */
function obtenerHoraNewYorkARQ() {
  const partes = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York", weekday: "short",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23"
  }).formatToParts(new Date());
  const datos = {};
  partes.forEach(p => { datos[p.type] = p.value; });
  return { weekday: datos.weekday, hour: Number(datos.hour), minute: Number(datos.minute) };
}

function mercadoAbiertoAhoraARQ() {
  const ny = obtenerHoraNewYorkARQ();
  const habil = ["Mon", "Tue", "Wed", "Thu", "Fri"].includes(ny.weekday);
  const min = ny.hour * 60 + ny.minute;
  return habil && min >= (9 * 60 + 30) && min < (16 * 60);
}

function mercadoPreAperturaARQ() {
  const ny = obtenerHoraNewYorkARQ();
  const habil = ["Mon", "Tue", "Wed", "Thu", "Fri"].includes(ny.weekday);
  const min = ny.hour * 60 + ny.minute;
  return habil && min >= (9 * 60) && min < (9 * 60 + 30);
}

function actualizarAvisoSistemaARQ() {
  const badge = $("marketStatusBadge");
  const texto = $("marketStatusText");
  if (!badge || !texto) return;
  badge.classList.remove("market-online", "market-off", "market-preopen");
  if (mercadoAbiertoAhoraARQ()) { badge.classList.add("market-online"); texto.textContent = "sistema en línea"; }
  else if (mercadoPreAperturaARQ()) { badge.classList.add("market-preopen"); texto.textContent = "preapertura"; }
  else { badge.classList.add("market-off"); texto.textContent = "sistema off"; }
}

/* ---------- Arranque ---------- */
cargarDatos();
setInterval(() => { if (!document.hidden) cargarDatos(); }, AUTO_REFRESH_MS);
actualizarAvisoSistemaARQ();
setInterval(actualizarAvisoSistemaARQ, 30000);
