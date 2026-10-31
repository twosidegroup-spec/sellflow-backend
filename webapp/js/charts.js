/* SellFlow console — hand-rolled SVG charts (no chart library).
   Real data only; every chart renders an empty state when there is nothing. */

import { esc, fmt } from "./ui.js";

const SVG_NS = "http://www.w3.org/2000/svg";

export function axisMoney(value) {
  const number = Number(value ?? 0);
  if (Math.abs(number) >= 1_000_000) return `৳${(number / 1_000_000).toFixed(1)}M`;
  if (Math.abs(number) >= 1_000) return `৳${Math.round(number / 1_000)}k`;
  return `৳${Math.round(number)}`;
}

function niceCeil(value) {
  if (value <= 0) return 100;
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const steps = [1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 7.5, 10];
  for (const step of steps) {
    if (value <= step * magnitude) return step * magnitude;
  }
  return 10 * magnitude;
}

function smoothPath(points) {
  if (points.length < 2) return "";
  let path = `M ${points[0][0]} ${points[0][1]}`;
  for (let index = 0; index < points.length - 1; index++) {
    const [x0, y0] = points[Math.max(0, index - 1)];
    const [x1, y1] = points[index];
    const [x2, y2] = points[index + 1];
    const [x3, y3] = points[Math.min(points.length - 1, index + 2)];
    const c1x = x1 + (x2 - x0) / 6;
    const c1y = y1 + (y2 - y0) / 6;
    const c2x = x2 - (x3 - x1) / 6;
    const c2y = y2 - (y3 - y1) / 6;
    path += ` C ${c1x.toFixed(1)} ${c1y.toFixed(1)}, ${c2x.toFixed(1)} ${c2y.toFixed(1)}, ${x2.toFixed(1)} ${y2.toFixed(1)}`;
  }
  return path;
}

/* ------------------------------------------------------------- area chart */

export function areaChart(container, { data, height = 210, format = (value) => fmt.money(value, { decimals: true }) }) {
  container.innerHTML = "";
  if (!data || data.length === 0 || data.every((point) => !Number(point.value))) {
    container.innerHTML = `<div class="state" style="padding:34px 10px">
      <span class="glyph">${'<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round"><path d="M3 12h4l3-8 4 16 3-8h4"/></svg>'}</span>
      <p>No revenue recorded yet. Sales will appear here as orders are created.</p>
    </div>`;
    return;
  }

  const width = 720;
  const padding = { top: 16, right: 14, bottom: 28, left: 52 };
  const innerWidth = width - padding.left - padding.right;
  const innerHeight = height - padding.top - padding.bottom;

  const values = data.map((point) => Number(point.value) || 0);
  const maxValue = niceCeil(Math.max(...values));
  const stepX = data.length > 1 ? innerWidth / (data.length - 1) : innerWidth;

  const points = data.map((point, index) => [
    padding.left + index * stepX,
    padding.top + innerHeight - ((Number(point.value) || 0) / maxValue) * innerHeight,
  ]);

  const gridLines = [0, 0.25, 0.5, 0.75, 1]
    .map((fraction) => {
      const y = padding.top + innerHeight - fraction * innerHeight;
      return `<line class="grid-line" x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}" ${
        fraction === 0 ? "" : 'stroke-dasharray="3 4"'
      }/>
      <text class="axis-label" x="${padding.left - 10}" y="${y + 3.5}" text-anchor="end">${esc(axisMoney(maxValue * fraction))}</text>`;
    })
    .join("");

  const labelEvery = Math.ceil(data.length / 7);
  const xLabels = data
    .map((point, index) => {
      if (index % labelEvery !== 0 && index !== data.length - 1) return "";
      const x = padding.left + index * stepX;
      return `<text class="axis-label" x="${x}" y="${height - 6}" text-anchor="middle">${esc(point.label)}</text>`;
    })
    .join("");

  const linePath = smoothPath(points);
  const areaPath = `${linePath} L ${points[points.length - 1][0]} ${padding.top + innerHeight} L ${points[0][0]} ${padding.top + innerHeight} Z`;
  const lastPoint = points[points.length - 1];

  container.innerHTML = `
    <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Revenue trend">
      <defs>
        <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#16C2AF" stop-opacity="0.30"/>
          <stop offset="100%" stop-color="#16C2AF" stop-opacity="0.02"/>
        </linearGradient>
      </defs>
      ${gridLines}
      ${xLabels}
      <path class="area" d="${areaPath}"/>
      <path class="line" d="${linePath}"/>
      <circle class="dot" cx="${lastPoint[0]}" cy="${lastPoint[1]}" r="4"/>
      <line class="hover-line" x1="0" x2="0" y1="${padding.top}" y2="${padding.top + innerHeight}" style="display:none"/>
      <circle class="dot" id="hover-dot" r="4.5" style="display:none"/>
      <rect id="hover-catcher" x="${padding.left - stepX / 2}" y="0" width="${innerWidth + stepX}" height="${height}" fill="transparent"/>
    </svg>`;

  const svg = container.querySelector("svg");
  const hoverLine = container.querySelector(".hover-line");
  const hoverDot = container.querySelector("#hover-dot");
  const tip = document.createElement("div");
  tip.className = "chart-tip";
  tip.style.display = "none";
  container.appendChild(tip);

  const catcher = container.querySelector("#hover-catcher");
  const move = (event) => {
    const rect = svg.getBoundingClientRect();
    const scaleX = width / rect.width;
    const localX = (event.clientX - rect.left) * scaleX;
    const index = Math.max(0, Math.min(data.length - 1, Math.round((localX - padding.left) / stepX)));
    const [x, y] = points[index];
    hoverLine.setAttribute("x1", x);
    hoverLine.setAttribute("x2", x);
    hoverDot.setAttribute("cx", x);
    hoverDot.setAttribute("cy", y);
    hoverLine.style.display = "";
    hoverDot.style.display = "";
    tip.style.display = "";
    tip.style.left = `${(x / width) * rect.width}px`;
    tip.style.top = `${(y / height) * rect.height}px`;
    tip.innerHTML = `<div class="t-label">${esc(data[index].label)}</div><div class="t-value">${esc(format(data[index].value))}</div>`;
  };
  catcher.addEventListener("pointermove", move);
  catcher.addEventListener("pointerleave", () => {
    hoverLine.style.display = "none";
    hoverDot.style.display = "none";
    tip.style.display = "none";
  });
}

/* ------------------------------------------------------------ donut chart */

export function donutChart(container, { segments, centerValue, centerLabel }) {
  const total = segments.reduce((sum, segment) => sum + (Number(segment.value) || 0), 0);
  if (!total) {
    container.innerHTML = `<div class="state" style="padding:30px 8px"><p>No payment activity yet.</p></div>`;
    return;
  }
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;
  const arcs = segments
    .filter((segment) => Number(segment.value) > 0)
    .map((segment) => {
      const fraction = Number(segment.value) / total;
      const dash = `${(fraction * circumference).toFixed(2)} ${(circumference * (1 - fraction)).toFixed(2)}`;
      const arc = `<circle cx="60" cy="60" r="${radius}" fill="none" stroke="${segment.color}"
        stroke-width="13" stroke-dasharray="${dash}" stroke-dashoffset="${(-offset * circumference).toFixed(2)}"
        stroke-linecap="butt"/>`;
      offset += fraction;
      return arc;
    })
    .join("");

  container.innerHTML = `
    <div class="donut">
      <svg viewBox="0 0 120 120" role="img" aria-label="Payment status mix">
        <circle cx="60" cy="60" r="${radius}" fill="none" stroke="var(--surface-3)" stroke-width="13"/>
        ${arcs}
      </svg>
      <div class="center">
        <span class="value">${esc(centerValue)}</span>
        <span class="label">${esc(centerLabel)}</span>
      </div>
    </div>
    <div class="legend">
      ${segments
        .map(
          (segment) => `
        <span class="item"><span class="swatch" style="background:${segment.color}"></span>
        ${esc(segment.label)} · <b style="color:var(--ink)">${fmt.num(segment.value)}</b></span>`
        )
        .join("")}
    </div>`;
}

/* -------------------------------------------------------------- sparkline */

export function sparkline(values, { width = 132, height = 34, stroke = "#16C2AF" } = {}) {
  if (!values || values.length < 2) return "";
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const span = max - min || 1;
  const stepX = width / (values.length - 1);
  const points = values.map((value, index) => [
    index * stepX,
    height - 4 - ((value - min) / span) * (height - 10),
  ]);
  const path = smoothPath(points);
  const area = `${path} L ${width} ${height} L 0 ${height} Z`;
  return `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}" preserveAspectRatio="none" aria-hidden="true">
    <defs><linearGradient id="spark-${stroke.replace("#", "")}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="${stroke}" stop-opacity="0.35"/><stop offset="100%" stop-color="${stroke}" stop-opacity="0"/>
    </linearGradient></defs>
    <path d="${area}" fill="url(#spark-${stroke.replace("#", "")})"/>
    <path d="${path}" fill="none" stroke="${stroke}" stroke-width="2" stroke-linecap="round"/>
  </svg>`;
}
