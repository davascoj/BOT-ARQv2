let datosGlobales = [];
let datosOriginales = [];
let sectorActivo = "TODOS";
let contextoMercado = null;
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
let resumenDiario = [];
let paperTradingV4 = null;
let paperAuditV43 = null;
let operationalRulesV44 = null;
let renderLazyInicializado = false;
let rankingRenderizado = false;
let historialRenderizado = false;
let metricasRenderizadas = false;
const AUTO_REFRESH_MS = 60 * 1000;
let autoRefreshActivo = true;

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
  if (!Number.isFinite(n)) return "";
  return n.toFixed(decimales).replace(/\.00$/, "");
}

function actualizarAutoRefreshInfo(mensaje = "") {
  const info = document.getElementById("autoRefreshInfo");
  if (!info) return;
  const hora = new Date().toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  info.textContent = mensaje || `Vista actualizada a las ${hora}. Se vuelve a refrescar sola cada 60 segundos. Los datos del mercado los actualiza GitHub Actions cada 5 minutos en horario de mercado.`;
}

function ejecutarBloqueSeguro(nombre, fn) {
  try {
    return fn();
  } catch (error) {
    console.error(`BOT-ARQ: error pintando ${nombre}`, error);
    const info = document.getElementById("autoRefreshInfo");
    if (info) {
      info.textContent = `Datos cargados, pero hubo un error visual en: ${nombre}. Revisa consola del navegador.`;
    }
    return null;
  }
}

async function cargarDatos() {
  const tabla = document.getElementById("tabla");
  const fecha = document.getElementById("fecha");
  const marketBox = document.getElementById("marketBox");
  const resumen = document.getElementById("resumen");
  const tablaHistorial = document.getElementById("tablaHistorial");

  tabla.innerHTML = `<tr><td colspan="20">Cargando datos...</td></tr>`;
  if (resumen) resumen.textContent = "Cargando resumen...";
  if (tablaHistorial) tablaHistorial.innerHTML = `<tr><td colspan="22">Cargando historial...</td></tr>`;

  try {
    const resp = await fetch("datos_acciones.json?nocache=" + Date.now());
    if (!resp.ok) throw new Error("No existe datos_acciones.json todavía");

    const data = await resp.json();
    fecha.textContent = "Última actualización: " + (data.actualizado || "sin fecha");
    actualizarAutoRefreshInfo();

    contextoMercado = data.contexto_mercado || null;
    datosGlobales = data.resultados || [];
    datosOriginales = data.resultados || [];
    historialOperaciones = data.historial?.operaciones || [];
    historialResumen = data.historial?.resumen || {};
    simulacionPro = historialResumen.simulacion || {};
    riesgoPro = historialResumen.riesgo || {};
    metricasPro = historialResumen.metricas || {};
    equityCurve = historialResumen.equity_curve || [];
    resumenDiario = historialResumen.resumen_diario || [];
    benchmarkBot = historialResumen.benchmark || {};
    rendimientoSectores = historialResumen.rendimiento_por_sector || [];
    rendimientoMercados = historialResumen.rendimiento_por_mercado || [];
    mejoresOperaciones = historialResumen.mejores_operaciones || [];
    peoresOperaciones = historialResumen.peores_operaciones || [];
    diagnosticoBot = historialResumen.diagnostico_bot || {};
    await cargarPaperTradingV4();

    const historialFecha = document.getElementById("historialFecha");
    if (historialFecha) historialFecha.textContent = "Actualizado: " + (data.historial?.actualizado || data.actualizado || "sin fecha");

    ejecutarBloqueSeguro("Mercado", pintarMercado);
    ejecutarBloqueSeguro("Resumen", pintarResumen);
    ejecutarBloqueSeguro("Panel ejecutivo", pintarDashboardEjecutivo);
    ejecutarBloqueSeguro("Alertas", pintarAlertasEjecutivas);
    ejecutarBloqueSeguro("Reglas operativas", pintarReglasOperativasV44);
    ejecutarBloqueSeguro("Auditoría de bloqueos", pintarAuditoriaBloqueos);
    ejecutarBloqueSeguro("Top oportunidades", renderTopOportunidades);
    ejecutarBloqueSeguro("Resumen historial", pintarHistorialResumen);
    ejecutarBloqueSeguro("Panel profesional", pintarPanelProfesional);
    ejecutarBloqueSeguro("Paper trading", pintarPaperTradingV4);
    ejecutarBloqueSeguro("Curva de capital", dibujarEquityCurve);
    ejecutarBloqueSeguro("Cartera abierta", renderCarteraAbierta);
    ejecutarBloqueSeguro("Render diferido", inicializarRenderDiferido);
    ejecutarBloqueSeguro("Vistas avanzadas", refrescarVistasAvanzadasSiAbiertas);

  } catch (e) {
    fecha.textContent = "Sin datos";
    actualizarAutoRefreshInfo("Sin datos cargados. Espera a que GitHub Actions termine la primera actualización automática o ejecútalo manualmente desde Actions.");
    if (marketBox) marketBox.textContent = "Mercado: sin datos";
    if (resumen) resumen.textContent = "No hay resumen disponible.";
    tabla.innerHTML = `<tr><td colspan="19">No se pudieron cargar datos todavía. Revisa que GitHub Actions haya terminado y que exista datos_acciones.json.</td></tr>`;
    if (tablaHistorial) tablaHistorial.innerHTML = `<tr><td colspan="22">No hay historial todavía.</td></tr>`;
  }
}



function campo(r, claves, fallback = "") {
  for (const k of claves) {
    const v = r?.[k];
    if (v !== undefined && v !== null && String(v).trim() !== "") return v;
  }
  return fallback;
}

function formatoNumeroCorto(v, dec = 2) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString("en-US", { maximumFractionDigits: dec, minimumFractionDigits: dec });
}

function formatoPrecio(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString("en-US", { maximumFractionDigits: 2, minimumFractionDigits: 2 });
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
    </div>
  `;
}

function textoAccionSugerida(r) {
  const bot = String(r?.["Senal Bot"] || "");
  const riesgo = String(r?.Riesgo || "");
  if (bot === "BUY STRONG" && riesgo === "BAJO") return "Prioritaria";
  if (bot === "BUY STRONG") return "Alta prioridad";
  if (bot === "BUY") return "Vigilar entrada";
  return "No abrir";
}

function pintarDashboardEjecutivo() {
  const box = document.getElementById("dashboardEjecutivo");
  if (!box) return;

  const sim = simulacionPro || {};
  const riesgo = riesgoPro || {};
  const met = metricasPro || {};
  const paperStatus = paperTradingV4?.status || {};
  const paperPortfolio = paperTradingV4?.portfolio || {};
  const estadoMercado = contextoMercado?.estado || "SIN DATOS";
  const brokerReal = paperStatus.broker_real_enabled ? "ON" : "OFF";

  box.innerHTML = `
    <div class="metric-box">
      <strong>${safe(estadoMercado)}</strong>
      <span>estado mercado</span>
    </div>
    <div class="metric-box">
      <strong>${paperStatus.health || "OK"}</strong>
      <span>salud V4</span>
    </div>
    <div class="metric-box">
      <strong>${dinero(sim.capital_actual_total_estimado ?? paperPortfolio.capital_initial_usd ?? 0)}</strong>
      <span>capital total estimado</span>
    </div>
    <div class="metric-box">
      <strong class="${claseValor(sim.ganancia_total_estimada_usd ?? paperPortfolio.total_pnl_usd_estimated)}">${dinero(sim.ganancia_total_estimada_usd ?? paperPortfolio.total_pnl_usd_estimated ?? 0)}</strong>
      <span>G/P total estimada</span>
    </div>
    <div class="metric-box">
      <strong>${riesgo.operaciones_abiertas ?? paperStatus.positions_open ?? 0}/${riesgo.max_operaciones_abiertas ?? ""}</strong>
      <span>operaciones abiertas</span>
    </div>
    <div class="metric-box">
      <strong>${numero(riesgo.exposicion_abierta_pct ?? paperPortfolio.exposure_pct ?? 0)}%</strong>
      <span>exposición abierta</span>
    </div>
    <div class="metric-box">
      <strong>${numero(riesgo.riesgo_total_abierto_pct ?? paperPortfolio.open_risk_pct ?? 0)}%</strong>
      <span>riesgo abierto</span>
    </div>
    <div class="metric-box">
      <strong>${brokerReal}</strong>
      <span>broker real</span>
    </div>
  `;
}

function pintarAlertasEjecutivas() {
  const box = document.getElementById("alertasEjecutivas");
  if (!box) return;

  const alertas = [];
  const riesgo = riesgoPro || {};
  const diag = diagnosticoBot || {};
  const paperWarnings = paperTradingV4?.status?.warnings || [];

  paperWarnings.forEach(w => alertas.push({tipo: "warning", texto: w}));

  const exp = Number(riesgo.exposicion_abierta_pct ?? 0);
  const risk = Number(riesgo.riesgo_total_abierto_pct ?? 0);
  const dd = Number(riesgo.max_drawdown_pct ?? 0);
  const abiertas = Number(riesgo.operaciones_abiertas ?? 0);
  const maxAbiertas = Number(riesgo.max_operaciones_abiertas ?? 0);

  if (maxAbiertas && abiertas >= maxAbiertas) alertas.push({tipo: "danger", texto: "Máximo de operaciones abiertas alcanzado."});
  if (exp > 80) alertas.push({tipo: "danger", texto: `Exposición abierta alta: ${numero(exp)}%.`});
  if (risk > 10) alertas.push({tipo: "danger", texto: `Riesgo abierto elevado: ${numero(risk)}%.`});
  if (dd > 20) alertas.push({tipo: "warning", texto: `Drawdown histórico relevante: -${numero(dd)}%.`});

  if (Array.isArray(diag.alertas)) {
    diag.alertas.slice(0, 4).forEach(a => alertas.push({tipo: "info", texto: a}));
  }

  if (!alertas.length) {
    box.innerHTML = `<div class="alert-item ok">Sin alertas críticas. Mantener monitoreo normal.</div>`;
    return;
  }

  const unicas = [];
  const vistos = new Set();
  alertas.forEach(a => {
    const key = String(a.texto || "").trim();
    if (key && !vistos.has(key)) {
      vistos.add(key);
      unicas.push(a);
    }
  });

  box.innerHTML = unicas.slice(0, 8).map(a => `
    <div class="alert-item ${a.tipo}">
      ${safe(a.texto)}
    </div>
  `).join("");
}

function renderTopOportunidades() {
  const tbody = document.getElementById("tablaTopOportunidades");
  if (!tbody) return;

  let datos = [...datosOriginales].filter(r =>
    ["BUY STRONG", "BUY"].includes(String(r["Senal Bot"] || "")) &&
    ["BAJO", "MEDIO"].includes(String(r.Riesgo || ""))
  );

  datos.sort(ordenRanking);
  datos = datos.slice(0, 10);

  if (!datos.length) {
    tbody.innerHTML = `<tr><td colspan="10">No hay oportunidades BUY con riesgo bajo/medio en este momento.</td></tr>`;
    return;
  }

  tbody.innerHTML = datos.map(r => {
    const precio = campo(r, ["Precio actual", "Precio"]);
    const stop = campo(r, ["Stop loss", "Stop"]);
    const objetivo = campo(r, ["Objetivo"]);
    const score = campo(r, ["Score calidad", "Score"], 0);
    const bot = String(r["Senal Bot"] || "");
    const accion = textoAccionSugerida(r);

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
        <td><span class="action-chip">${safe(accion)}</span></td>
      </tr>
    `;
  }).join("");
}


function pintarMercado() {
  const marketBox = document.getElementById("marketBox");
  if (!marketBox) return;

  if (!contextoMercado) {
    marketBox.textContent = "Mercado: sin datos";
    marketBox.className = "market-box";
    return;
  }

  const estado = contextoMercado.estado || "NEUTRO";
  const spy = contextoMercado.spy20 ?? 0;
  const qqq = contextoMercado.qqq20 ?? 0;

  marketBox.textContent = `Mercado: ${estado} | SPY 20D: ${spy}% | QQQ 20D: ${qqq}%`;
  marketBox.className = "market-box " + estado.toLowerCase().replace(" ", "-").replace("é", "e").replace("+", "plus");
}

function pintarResumen() {
  const resumen = document.getElementById("resumen");
  if (!resumen) return;

  const total = datosOriginales.length;
  const fuertes = datosOriginales.filter(r => r.Senal === "COMPRA FUERTE").length;
  const posibles = datosOriginales.filter(r => r.Senal === "POSIBLE COMPRA").length;
  const botBuy = datosOriginales.filter(r => ["BUY STRONG", "BUY"].includes(String(r["Senal Bot"] || ""))).length;
  const alto = datosOriginales.filter(r => r.Riesgo === "ALTO").length;

  resumen.innerHTML = `
    <div><strong>${total}</strong><span>acciones analizadas</span></div>
    <div><strong>${fuertes}</strong><span>compra fuerte</span></div>
    <div><strong>${posibles}</strong><span>posible compra</span></div>
    <div><strong>${botBuy}</strong><span>señales BUY</span></div>
    <div><strong>${alto}</strong><span>riesgo alto</span></div>
  `;
}

function pintarHistorialResumen() {
  const caja = document.getElementById("historialResumen");
  if (!caja) return;

  const r = historialResumen || {};
  caja.innerHTML = `
    <div><strong>${r.abiertas ?? 0}</strong><span>abiertas</span></div>
    <div><strong>${r.cerradas ?? 0}</strong><span>cerradas</span></div>
    <div><strong>${r.ganadas ?? 0}</strong><span>ganadas</span></div>
    <div><strong>${r.perdidas ?? 0}</strong><span>perdidas</span></div>
    <div><strong>${numero(r.win_rate ?? 0)}%</strong><span>acierto cerrado</span></div>
    <div><strong>${numero(r.rentabilidad_cerrada_pct ?? 0)}%</strong><span>rentab. cerrada</span></div>
    <div><strong>${numero(r.rentabilidad_abierta_pct ?? 0)}%</strong><span>rentab. abierta</span></div>
  `;
}

function dinero(valor) {
  const n = Number(valor);
  if (!Number.isFinite(n)) return "$0";
  return n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });
}

function claseValor(n) {
  const v = Number(n || 0);
  return v >= 0 ? "valor-pos" : "valor-neg";
}

function pintarPanelProfesional() {
  const sim = simulacionPro || {};
  const riesgo = riesgoPro || {};
  const met = metricasPro || {};
  const diag = diagnosticoBot || {};

  const resumen = document.getElementById("simulacionResumen");
  if (resumen) {
    resumen.innerHTML = `
      <div class="metric-box"><strong>${dinero(sim.capital_inicial ?? 0)}</strong><span>capital inicial</span></div>
      <div class="metric-box"><strong>${dinero(sim.capital_actual_total_estimado ?? 0)}</strong><span>capital total c/abiertas</span></div>
      <div class="metric-box"><strong class="${claseValor(sim.ganancia_total_estimada_usd)}">${dinero(sim.ganancia_total_estimada_usd ?? 0)}</strong><span>G/P total estimada</span></div>
      <div class="metric-box"><strong class="${claseValor(sim.rentabilidad_total_estimada_pct)}">${numero(sim.rentabilidad_total_estimada_pct ?? 0)}%</strong><span>rentabilidad total</span></div>
      <div class="metric-box"><strong>${numero(met.profit_factor ?? 0)}</strong><span>profit factor</span></div>
      <div class="metric-box"><strong>${numero(met.expectativa_pct_por_operacion ?? 0)}%</strong><span>expectativa/op</span></div>
      <div class="metric-box"><strong class="${claseValor(benchmarkBot.bot_vs_spy_alpha_pct)}">${numero(benchmarkBot.bot_vs_spy_alpha_pct ?? 0)}%</strong><span>bot vs SPY</span></div>
      <div class="metric-box"><strong class="${claseValor(benchmarkBot.bot_vs_qqq_alpha_pct)}">${numero(benchmarkBot.bot_vs_qqq_alpha_pct ?? 0)}%</strong><span>bot vs QQQ</span></div>
    `;
  }

  const riesgoCaja = document.getElementById("riesgoResumen");
  if (riesgoCaja) {
    riesgoCaja.innerHTML = `
      <div><strong class="valor-neg">-${numero(riesgo.max_drawdown_pct ?? 0)}%</strong><span>máx. drawdown</span></div>
      <div><strong>${riesgo.racha_max_perdidas ?? 0}</strong><span>racha pérdidas</span></div>
      <div><strong>${riesgo.operaciones_abiertas ?? 0}/${riesgo.max_operaciones_abiertas ?? 0}</strong><span>operaciones abiertas</span></div>
      <div><strong>${numero(riesgo.exposicion_abierta_pct ?? 0)}%</strong><span>exposición</span></div>
      <div><strong>${numero(riesgo.riesgo_total_abierto_pct ?? 0)}%</strong><span>riesgo abierto</span></div>
      <div><strong>${dinero(riesgo.riesgo_total_abierto_usd ?? 0)}</strong><span>riesgo USD</span></div>
    `;
  }

  const diagCaja = document.getElementById("diagnosticoBot");
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
      <p class="mini-copy">Costo estimado/op: ${numero(met.costo_total_pct_estimado ?? 0)}%. Benchmark: SPY ${numero(benchmarkBot.spy_pct ?? 0)}%, QQQ ${numero(benchmarkBot.qqq_pct ?? 0)}%.</p>
    `;
  }
}

function dibujarEquityCurve() {
  const canvas = document.getElementById("equityChart");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#0f172a";
  ctx.fillRect(0, 0, w, h);

  const puntos = Array.isArray(equityCurve) ? equityCurve : [];
  if (puntos.length < 2) {
    ctx.fillStyle = "#cbd5e1";
    ctx.font = "18px Arial";
    ctx.fillText("Aún no hay suficientes operaciones cerradas para dibujar curva de capital.", 30, 60);
    return;
  }

  const margen = 42;
  const valores = puntos.map(p => Number(p.capital || 0)).filter(Number.isFinite);
  const min = Math.min(...valores);
  const max = Math.max(...valores);
  const rango = Math.max(max - min, 1);

  ctx.strokeStyle = "#334155";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const y = margen + ((h - margen * 2) * i / 4);
    ctx.beginPath();
    ctx.moveTo(margen, y);
    ctx.lineTo(w - margen, y);
    ctx.stroke();
  }

  ctx.strokeStyle = "#38bdf8";
  ctx.lineWidth = 3;
  ctx.beginPath();
  puntos.forEach((p, i) => {
    const x = margen + ((w - margen * 2) * i / (puntos.length - 1));
    const y = h - margen - (((Number(p.capital || 0) - min) / rango) * (h - margen * 2));
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  ctx.fillStyle = "#e2e8f0";
  ctx.font = "13px Arial";
  ctx.fillText(`Máx: ${dinero(max)}`, margen, 22);
  ctx.fillText(`Mín: ${dinero(min)}`, margen, h - 12);
  const ultimo = puntos[puntos.length - 1];
  ctx.fillText(`Actual cerrado: ${dinero(ultimo.capital || 0)}`, w - 245, 22);
}

function llenarTablaSimple(id, filas, tipo) {
  const tbody = document.getElementById(id);
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

function filtrarSector(sector) {
  datosGlobales = [...datosOriginales];
  sectorActivo = sector;
  const ranking = document.getElementById("rankingCompletoDetails");
  if (ranking) ranking.open = true;
  rankingRenderizado = true;
  renderTabla();
}

function limpiarBusqueda() {
  const buscar = document.getElementById("buscarAccion");
  if (buscar) buscar.value = "";

  datosGlobales = [...datosOriginales];
  sectorActivo = "TODOS";

  const soloCompra = document.getElementById("soloCompra");
  const soloHot = document.getElementById("soloHot");
  const ocultarAlto = document.getElementById("ocultarAlto");

  if (soloCompra) soloCompra.checked = false;
  if (soloHot) soloHot.checked = false;
  if (ocultarAlto) ocultarAlto.checked = false;

  const ranking = document.getElementById("rankingCompletoDetails");
  if (ranking) ranking.open = true;
  rankingRenderizado = true;
  renderTabla();
}

function claseProbabilidad(prob) {
  if (prob >= 84) return "prob-verde";
  if (prob >= 70) return "prob-amarillo";
  return "prob-rojo";
}

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

function mostrarTop4() {
  let datos = [...datosOriginales];

  datos = datos.filter(r =>
    ["BUY STRONG", "BUY"].includes(String(r["Senal Bot"] || "")) &&
    ["BAJO", "MEDIO"].includes(r.Riesgo)
  );

  datos.sort(ordenRanking);
  datosGlobales = datos.slice(0, 4);
  sectorActivo = "TODOS";

  const buscar = document.getElementById("buscarAccion");
  const soloCompra = document.getElementById("soloCompra");
  const soloHot = document.getElementById("soloHot");
  const ocultarAlto = document.getElementById("ocultarAlto");

  if (buscar) buscar.value = "";
  if (soloCompra) soloCompra.checked = false;
  if (soloHot) soloHot.checked = false;
  if (ocultarAlto) ocultarAlto.checked = false;

  renderTabla();
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

function claseBot(bot) {
  const b = String(bot || "");
  if (b === "BUY STRONG") return "bot-buy-strong";
  if (b === "BUY") return "bot-buy";
  if (b === "HOLD") return "bot-hold";
  return "bot-sell";
}

function renderTabla() {
  const tabla = document.getElementById("tabla");
  const soloCompra = document.getElementById("soloCompra")?.checked || false;
  const soloHot = document.getElementById("soloHot")?.checked || false;
  const ocultarAlto = document.getElementById("ocultarAlto")?.checked || false;
  const busqueda = document.getElementById("buscarAccion")?.value.trim().toUpperCase() || "";

  let datos = [...datosGlobales];

  if (sectorActivo !== "TODOS") {
    datos = datos.filter(r => String(r.Sector || "").includes(sectorActivo));
  }

  if (busqueda !== "") {
    datos = datos.filter(r => String(r.Accion || "").toUpperCase().includes(busqueda));
  }

  if (soloCompra) {
    datos = datos.filter(r => ["BUY STRONG", "BUY"].includes(String(r["Senal Bot"] || "")));
  }

  if (soloHot) {
    datos = datos.filter(r => String(r["Hot Score"] || "").includes("🔥"));
  }

  if (ocultarAlto) {
    datos = datos.filter(r => String(r.Riesgo || "") !== "ALTO");
  }

  datos.sort(ordenRanking);
  tabla.innerHTML = "";

  if (datos.length === 0) {
    tabla.innerHTML = `<tr><td colspan="20">No hay resultados con esos filtros.</td></tr>`;
    return;
  }

  datos.forEach(r => {
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

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>${safe(r.Accion)}</strong></td>
      <td>${safe(r.Sector || "Otro")}</td>
      <td>${safe(r["Precio actual"])}</td>
      <td><span class="prob ${claseProbabilidad(prob)}">${numero(prob, 1)}%</span></td>
      <td class="${claseMom}">${numero(momentum)}%</td>
      <td class="${claseRel}">${numero(fuerzaRel)}%</td>
      <td>${safe(r["Hot Score"] || "")}</td>
      <td><span class="conf ${String(r.Confirmacion || "MEDIA").toLowerCase()}">${safe(r.Confirmacion || "MEDIA")}</span></td>
      <td>${safe(r["ATR %"] || 0)}%</td>
      <td>${safe(r["Entrada min"])} - ${safe(r["Entrada max"])}</td>
      <td>${safe(r["Stop loss"])}</td>
      <td>${safe(r.Objetivo)}</td>
      <td>${safe(r["R/R"] || "")}</td>
      <td>${safe(r.RSI)}</td>
      <td>${safe(r.Mercado || "NEUTRO")}</td>
      <td><span class="badge ${riesgo}">${safe(r.Riesgo)}</span></td>
      <td class="${claseSenal}">${safe(r.Senal)}</td>
      <td><span class="score-pill ${claseScore(r["Score calidad"])}">${numero(r["Score calidad"] ?? 0, 1)}</span></td>
      <td><span class="bot-badge ${claseBot(bot)}">${safe(bot)}</span></td>
      <td class="detalle" title="${safe(detalle)}">${safe(detalle || "-")}</td>
    `;

    tabla.appendChild(tr);
  });
}

function claseScore(score) {
  const s = Number(score || 0);
  if (s >= 80) return "score-alto";
  if (s >= 60) return "score-medio";
  return "score-bajo";
}

function renderCarteraAbierta() {
  const tbody = document.getElementById("tablaCarteraAbierta");
  if (!tbody) return;
  const abiertas = historialOperaciones
    .filter(op => String(op.estado || "") === "ABIERTA")
    .sort((a, b) => Number(b.score_calidad_actual || 0) - Number(a.score_calidad_actual || 0));

  if (abiertas.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10">No hay operaciones abiertas actualmente.</td></tr>`;
    return;
  }

  tbody.innerHTML = abiertas.slice(0, 40).map(op => {
    const gananciaPct = Number(op.ganancia_pct ?? 0);
    const botActual = op.senal_bot_actual || op.senal_bot_entrada || "";
    return `<tr>
      <td><strong>${safe(op.accion)}</strong></td>
      <td>${safe(op.sector || "Otro")}</td>
      <td>${dinero(op.valor_cartera_usd ?? op.posicion_usd_estimada ?? 0)}</td>
      <td class="${claseValor(op.ganancia_abierta_usd_estimada ?? op.pnl_usd_estimado)}">${dinero(op.ganancia_abierta_usd_estimada ?? op.pnl_usd_estimado ?? 0)}</td>
      <td class="${gananciaPct >= 0 ? "hist-pos" : "hist-neg"}">${numero(gananciaPct)}%</td>
      <td class="valor-neg">${dinero(op.perdida_maxima_stop_usd ?? op.riesgo_usd_estimado ?? 0)}</td>
      <td>${numero(op.distancia_objetivo_pct ?? 0)}%</td>
      <td>${numero(op.distancia_stop_actual_pct ?? op.distancia_stop_pct ?? 0)}%</td>
      <td><span class="score-pill ${claseScore(op.score_calidad_actual ?? op.score_calidad_entrada)}">${numero(op.score_calidad_actual ?? op.score_calidad_entrada ?? 0, 1)}</span></td>
      <td><span class="bot-badge ${claseBot(botActual)}">${safe(botActual)}</span></td>
    </tr>`;
  }).join("");
}

function renderHistorial() {
  const tabla = document.getElementById("tablaHistorial");
  if (!tabla) return;

  tabla.innerHTML = "";
  const busqueda = document.getElementById("buscarHistorial")?.value.trim().toUpperCase() || "";
  const estadoFiltro = document.getElementById("filtroEstadoHistorial")?.value || "TODOS";
  const resultadoFiltro = document.getElementById("filtroResultadoHistorial")?.value || "TODOS";

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
    tabla.innerHTML = `<tr><td colspan="22">Todavía no hay historial. Ejecuta el análisis una vez y la app empezará a guardar señales.</td></tr>`;
    return;
  }

  ops.slice(0, 120).forEach(op => {
    const estado = String(op.estado || "");
    const ganancia = Number(op.estado === "CERRADA" ? (op.ganancia_pct_final ?? op.ganancia_pct ?? 0) : (op.ganancia_pct ?? 0));
    const claseGanancia = ganancia >= 0 ? "hist-pos" : "hist-neg";
    const claseEstado = estado === "ABIERTA" ? "hist-open" : "hist-closed";
    const botActual = op.senal_bot_actual || op.senal_bot_entrada || "";

    const tr = document.createElement("tr");
    const gpUsd = op.estado === "ABIERTA" ? (op.ganancia_abierta_usd_estimada ?? op.pnl_usd_estimado ?? 0) : (op.pnl_usd_estimado ?? 0);
    tr.innerHTML = `
      <td><span class="hist-status ${claseEstado}">${safe(estado)}</span></td>
      <td><strong>${safe(op.accion)}</strong></td>
      <td>${safe(op.precio_entrada)}</td>
      <td>${safe(op.precio_actual ?? op.precio_cierre ?? "")}</td>
      <td class="${claseGanancia}">${numero(ganancia)}%</td>
      <td>${dinero(op.posicion_usd_estimada ?? 0)}</td>
      <td>${dinero(op.valor_cartera_usd ?? 0)}</td>
      <td class="${claseValor(gpUsd)}">${dinero(gpUsd)}</td>
      <td>${dinero(op.riesgo_usd_estimado ?? 0)}</td>
      <td>${numero(op.riesgo_pct_cuenta_estimado ?? 0)}%</td>
      <td>${dinero(op.costo_usd_estimado ?? 0)}</td>
      <td>${numero(op.distancia_objetivo_pct ?? 0)}%</td>
      <td>${numero(op.distancia_stop_actual_pct ?? op.distancia_stop_pct ?? 0)}%</td>
      <td><span class="score-pill ${claseScore(op.score_calidad_actual ?? op.score_calidad_entrada)}">${numero(op.score_calidad_actual ?? op.score_calidad_entrada ?? 0, 1)}</span></td>
      <td>${safe(op.stop)}</td>
      <td>${safe(op.objetivo)}</td>
      <td>${safe(op.rr || "")}</td>
      <td>${safe(op.fecha_entrada)}</td>
      <td>${safe(op.dias_abierta ?? 0)}</td>
      <td>${safe(op.senal_entrada)}</td>
      <td><span class="bot-badge ${claseBot(botActual)}">${safe(botActual)}</span></td>
      <td>${safe(op.resultado || "EN SEGUIMIENTO")}</td>
    `;
    tabla.appendChild(tr);
  });
}


function inicializarRenderDiferido() {
  if (renderLazyInicializado) return;
  renderLazyInicializado = true;

  const ranking = document.getElementById("rankingCompletoDetails");
  const hist = document.getElementById("historialCard");
  const metricas = document.getElementById("metricasAvanzadasDetails");

  if (ranking) {
    ranking.addEventListener("toggle", () => {
      if (ranking.open) {
        rankingRenderizado = true;
        renderTabla();
      }
    });
  }

  if (hist) {
    hist.addEventListener("toggle", () => {
      if (hist.open) {
        historialRenderizado = true;
        pintarHistorialResumen();
        renderHistorial();
      }
    });
  }

  if (metricas) {
    metricas.addEventListener("toggle", () => {
      if (metricas.open) {
        metricasRenderizadas = true;
        renderTablasAvanzadas();
      }
    });
  }
}

function refrescarVistasAvanzadasSiAbiertas() {
  const ranking = document.getElementById("rankingCompletoDetails");
  const hist = document.getElementById("historialCard");
  const metricas = document.getElementById("metricasAvanzadasDetails");

  const tablaRanking = document.getElementById("tabla");
  if (ranking?.open) {
    rankingRenderizado = true;
    renderTabla();
  } else if (tablaRanking) {
    tablaRanking.innerHTML = `<tr><td colspan="20">Abra esta sección para cargar el ranking completo. Esto mejora la velocidad de la página.</td></tr>`;
  }

  if (hist?.open) {
    historialRenderizado = true;
    renderHistorial();
  } else {
    const tablaHistorial = document.getElementById("tablaHistorial");
    if (tablaHistorial) tablaHistorial.innerHTML = `<tr><td colspan="22">Abra esta sección para cargar el historial completo.</td></tr>`;
  }

  if (metricas?.open) {
    metricasRenderizadas = true;
    renderTablasAvanzadas();
  }
}

function scrollHistorial() {
  const card = document.getElementById("historialCard");
  if (card) {
    card.open = true;
    historialRenderizado = true;
    renderHistorial();
    card.scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

function ejecutarAnalisis() {
  const usuario = "davascoj";
  const repoDetectado = location.pathname.split("/").filter(Boolean)[0];
  const repo = repoDetectado || "Analizador-acciones";
  const workflow = "analizar.yml";
  const url = `https://github.com/${usuario}/${repo}/actions/workflows/${workflow}`;
  window.open(url, "_blank");
  alert("Ya no necesitas token desde la página. Se abrió GitHub Actions. Ahí puedes usar Run workflow si quieres forzar una actualización manual.");
}

cargarDatos();

setInterval(() => {
  if (!document.hidden && autoRefreshActivo) {
    cargarDatos();
  }
}, AUTO_REFRESH_MS);


// ================================
// AVISO VISUAL DE ESTADO DEL SISTEMA
// Mercado regular NYSE/Nasdaq: lunes a viernes, 9:30 a.m. a 4:00 p.m. New York
// Nota: no valida feriados especiales; el workflow de Python sí controla eso mejor.
// ================================
function obtenerHoraNewYorkARQ() {
  const partes = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hourCycle: "h23"
  }).formatToParts(new Date());

  const datos = {};

  partes.forEach((parte) => {
    datos[parte.type] = parte.value;
  });

  return {
    weekday: datos.weekday,
    hour: Number(datos.hour),
    minute: Number(datos.minute),
    second: Number(datos.second)
  };
}

function mercadoAbiertoAhoraARQ() {
  const ny = obtenerHoraNewYorkARQ();
  const diasHabiles = ["Mon", "Tue", "Wed", "Thu", "Fri"];
  const esDiaHabil = diasHabiles.includes(ny.weekday);
  const minutosActuales = ny.hour * 60 + ny.minute;
  const apertura = 9 * 60 + 30;
  const cierre = 16 * 60;

  return esDiaHabil && minutosActuales >= apertura && minutosActuales < cierre;
}

function mercadoPreAperturaARQ() {
  const ny = obtenerHoraNewYorkARQ();
  const diasHabiles = ["Mon", "Tue", "Wed", "Thu", "Fri"];
  const esDiaHabil = diasHabiles.includes(ny.weekday);
  const minutosActuales = ny.hour * 60 + ny.minute;
  const preInicio = 9 * 60;
  const apertura = 9 * 60 + 30;

  return esDiaHabil && minutosActuales >= preInicio && minutosActuales < apertura;
}

function actualizarAvisoSistemaARQ() {
  const badge = document.getElementById("marketStatusBadge");
  const texto = document.getElementById("marketStatusText");

  if (!badge || !texto) return;

  badge.classList.remove("market-online", "market-off", "market-preopen");

  if (mercadoAbiertoAhoraARQ()) {
    badge.classList.add("market-online");
    texto.textContent = "sistema en línea";
  } else if (mercadoPreAperturaARQ()) {
    badge.classList.add("market-preopen");
    texto.textContent = "preapertura";
  } else {
    badge.classList.add("market-off");
    texto.textContent = "sistema off";
  }
}

actualizarAvisoSistemaARQ();
setInterval(actualizarAvisoSistemaARQ, 30000);



async function cargarPaperTradingV4() {
  try {
    const resp = await fetch("paper/paper_state.json?nocache=" + Date.now());
    if (!resp.ok) throw new Error("No existe paper_state.json");
    paperTradingV4 = await resp.json();
    paperAuditV43 = paperTradingV4.audit || null;
    operationalRulesV44 = paperTradingV4.operational_rules || paperTradingV4.risk?.operational_rules || null;
  } catch (e) {
    paperTradingV4 = null;
    paperAuditV43 = null;
    operationalRulesV44 = null;
  }
}



function pintarReglasOperativasV44() {
  const box = document.getElementById("operationalRulesResumen");
  const badge = document.getElementById("operationalRulesBadge");
  if (!box) return;
  if (!operationalRulesV44) {
    box.innerHTML = `<div class="metric-box">Reglas operativas pendientes. Se llenarán en la próxima ejecución del bot.</div>`;
    if (badge) { badge.textContent = "Pendiente"; badge.className = "mode-badge v4-badge warning"; }
    return;
  }
  const estado = operationalRulesV44.estado || "NORMAL";
  if (badge) { badge.textContent = estado; badge.className = "mode-badge v4-badge " + (estado === "NORMAL" ? "ok" : "warning"); }
  const reglas = operationalRulesV44.reglas_activas || {};
  box.innerHTML = `
    <div class="metric-box"><strong>${safe(estado)}</strong><span>estado operativo</span></div>
    <div class="metric-box"><strong>${numero(operationalRulesV44.exposicion_abierta_pct ?? 0)}%</strong><span>exposición actual / máx ${numero(operationalRulesV44.max_exposicion_total_pct ?? 0)}%</span></div>
    <div class="metric-box"><strong>${numero(operationalRulesV44.riesgo_abierto_pct ?? 0)}%</strong><span>riesgo abierto / máx ${numero(operationalRulesV44.max_riesgo_total_abierto_pct ?? 0)}%</span></div>
    <div class="metric-box"><strong>${numero(operationalRulesV44.drawdown_pct ?? 0)}%</strong><span>drawdown máx. bloqueo ${numero(operationalRulesV44.bloquear_entradas_drawdown_pct ?? 0)}%</span></div>
    <div class="metric-box"><strong>${safe(operationalRulesV44.bloqueos_generados ?? 0)}</strong><span>bloqueos generados</span></div>
    <div class="metric-box"><strong>${safe(operationalRulesV44.motivo_principal || "SIN BLOQUEOS")}</strong><span>motivo principal</span></div>
    <div class="metric-box"><strong>${reglas.exposicion ? "ON" : "OFF"}</strong><span>bloqueo exposición</span></div>
    <div class="metric-box"><strong>${reglas.drawdown ? "ON" : "OFF"}</strong><span>bloqueo drawdown</span></div>`;
}


function pintarAuditoriaBloqueos() {
  const summary = document.getElementById("auditSummary");
  const tbody = document.getElementById("tablaBloqueos");
  const badge = document.getElementById("auditBadge");

  if (!summary || !tbody) return;

  if (!paperAuditV43) {
    summary.innerHTML = `<div class="metric-box">Auditoría pendiente. Se llenará en la próxima ejecución del bot.</div>`;
    tbody.innerHTML = `<tr><td colspan="6">Sin auditoría disponible todavía.</td></tr>`;
    if (badge) badge.textContent = "Pendiente";
    return;
  }

  const s = paperAuditV43.summary || {};
  const blocked = paperAuditV43.blocked_signals || [];
  const reasons = paperAuditV43.block_reasons || [];

  if (badge) badge.textContent = `${s.blocked_count || 0} bloqueadas`;

  summary.innerHTML = `
    <div class="metric-box"><strong>${s.blocked_count || 0}</strong><span>señales bloqueadas</span></div>
    <div class="metric-box"><strong>${s.buy_candidates_count || 0}</strong><span>candidatas BUY</span></div>
    <div class="metric-box"><strong>${s.open_positions_count || 0}</strong><span>posiciones abiertas</span></div>
    <div class="metric-box"><strong>${safe(s.main_block_reason || "Sin bloqueos")}</strong><span>motivo principal</span></div>
  `;

  if (!blocked.length) {
    tbody.innerHTML = `<tr><td colspan="6">No hay señales bloqueadas registradas.</td></tr>`;
    return;
  }

  tbody.innerHTML = blocked.slice(0, 12).map(b => `
    <tr>
      <td class="ticker-cell"><strong>${safe(b.ticker)}</strong></td>
      <td><span class="bot-badge ${claseBot(b.signal)}">${safe(b.signal)}</span></td>
      <td><span class="badge ${String(b.risk || "").toLowerCase()}">${safe(b.risk)}</span></td>
      <td class="num">${numero(b.rr ?? 0, 2)}</td>
      <td>${b.operational_rule ? '<span class="op-rule-dot">OP</span> ' : ''}${safe(b.reason)}</td>
      <td>${safe(b.date)}</td>
    </tr>
  `).join("");
}

function pintarPaperTradingV4() {
  const box = document.getElementById("paperV4Resumen");
  const health = document.getElementById("paperV4Health");
  const warnings = document.getElementById("paperV4Warnings");

  if (!box) return;

  if (!paperTradingV4 || !paperTradingV4.status) {
    box.innerHTML = `<div class="metric-box">Motor V4 pendiente. Espera la próxima ejecución de GitHub Actions.</div>`;
    if (health) {
      health.textContent = "V4 pendiente";
      health.className = "mode-badge v4-badge warning";
    }
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
    <div class="metric-box">
      <strong>${safe(status.positions_open ?? 0)}</strong>
      <span>posiciones paper abiertas</span>
    </div>
    <div class="metric-box">
      <strong>${safe(status.orders_total ?? 0)}</strong>
      <span>órdenes simuladas</span>
    </div>
    <div class="metric-box">
      <strong>${safe(status.trades_closed ?? 0)}</strong>
      <span>trades cerrados</span>
    </div>
    <div class="metric-box">
      <strong>$${numero(portfolio.exposure_usd ?? 0, 2)}</strong>
      <span>exposición paper</span>
    </div>
    <div class="metric-box">
      <strong>$${numero(portfolio.open_risk_usd ?? 0, 2)}</strong>
      <span>riesgo abierto paper</span>
    </div>
    <div class="metric-box">
      <strong>$${numero(portfolio.total_pnl_usd_estimated ?? 0, 2)}</strong>
      <span>G/P total estimada</span>
    </div>
    <div class="metric-box">
      <strong>${numero(risk.remaining_position_slots ?? 0, 0)}</strong>
      <span>cupos disponibles</span>
    </div>
    <div class="metric-box">
      <strong>${safe(status.broker_real_enabled ? "ON" : "OFF")}</strong>
      <span>broker real</span>
    </div>
  `;

  if (warnings) {
    warnings.innerHTML = warningList.length
      ? `<strong>Alertas V4:</strong><ul>${warningList.map(w => `<li>${safe(w)}</li>`).join("")}</ul>`
      : `<span class="paper-ok">Sin alertas críticas del motor V4.</span>`;
  }
}

