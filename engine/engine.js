/* Shared animation engine for every chapter page (copied from L0's intro.html and extended).
 *
 * A chapter page provides: <div id="stage"> with <section class="scene" id="S0..Sn"> blocks, then
 *   <script src="<build>/timelines/timeline_<id>.js"></script><script src="<root>/engine/engine.js"></script>
 *   <script> ENGINE.build(() => { ...dynamic content... }); ENGINE.start(); </script>
 *
 * data-at specs: "s+0.3" (slide start), "u3" (unit 3 start), "u3@across" (when "across" is spoken in unit 3),
 * "p5" (subtitle part 5 start), optional "f0.4" fraction of that unit/part, optional "+0.2"/"-0.2" offsets.
 * Extra kinds: data-kind="zoom" (data-zoom="dx,dy,scale", data-origin="x,y"), class "travel" (dot along data-path),
 * class "pulse" (expanding ring). data-out="<spec>" fades a popped element out again (hand-over to a later element).
 * data-kind="bloom": grows from a small seed to full size with a slight overshoot (e.g. where a travelling dot arrives).
 * data-kind="scaley": rises from its bottom edge (e.g. a pillar).
 */
(function () {
const TL = window.TIMELINE;
const SVGNS = "http://www.w3.org/2000/svg";
const W = "#fff", R = "#E93A3A", PURPLE = "#3D1E6D", BLUE = "#1B2F6B";

// ---------- icons: 100x100 box, white strokes + red accents ----------
const st = (c, w = 5) => `fill="none" stroke="${c}" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"`;
const ICONS = {
  headbulb: `<path ${st(W,5)} d="M34 92V76C20 69 15 54 19 40C24 22 40 11 57 13C75 15 87 30 85 48L91 61L83 63V73C83 80 77 82 71 80L64 79V92"/>
             <path ${st(W,4)} d="M44 52C44 42 51 35 59 35C67 35 74 42 74 52C74 58 70 61 68 65V70H51V65C48 61 44 58 44 52Z"/>
             <circle cx="59" cy="46" r="4" ${st(R,4)}/><path ${st(R,4)} d="M59 52V62M55 58L59 62L63 58"/>`,
  sparkles: `<path ${st(W,4)} d="M30 30L36 44L50 50L36 56L30 70L24 56L10 50L24 44Z"/>
             <path ${st(W,4)} d="M72 62L76 71L85 75L76 79L72 88L68 79L59 75L68 71Z"/>
             <circle cx="70" cy="22" r="6" ${st(R,4)}/><circle cx="20" cy="88" r="5" ${st(R,4)}/>
             <circle cx="88" cy="40" r="2.5" fill="${R}"/><circle cx="52" cy="14" r="2.5" fill="${W}"/>`,
  badge: `<circle cx="50" cy="42" r="28" ${st(W,5)}/><path ${st(W,5)} d="M34 64L28 92L50 82L72 92L66 64"/>
          <path ${st(R,5)} d="M38 42L47 51L63 34"/>`,
  chat: `<path ${st(W,5)} d="M14 22H86V68H46L28 84V68H14Z"/><path ${st(R,5)} d="M36 45L46 55L65 36"/>`,
  cube: `<path ${st(W,5)} d="M50 12L86 30V70L50 88L14 70V30Z"/><path ${st(W,5)} d="M14 30L50 48L86 30M50 48V88"/>
         <path ${st(R,4)} d="M32 21L68 39"/>`,
  doc: `<path ${st(W,5)} d="M24 10H62L80 28V90H24Z"/><path ${st(W,5)} d="M62 10V28H80"/>
        <path ${st(R,5)} d="M36 46H68M36 60H68M36 74H56"/>`,
  mail: `<rect x="12" y="24" width="76" height="54" rx="5" ${st(W,5)}/><path ${st(R,5)} d="M14 28L50 56L86 28"/>`,
  drive: `<path ${st(W,5)} d="M10 30V80H90V38H50L42 26H14Z"/><circle cx="38" cy="60" r="5" ${st(R,4)}/><circle cx="64" cy="50" r="5" ${st(R,4)}/><circle cx="64" cy="70" r="5" ${st(R,4)}/><path ${st(R,3)} d="M43 58L59 52M43 62L59 68"/>`,
  site: `<rect x="10" y="16" width="80" height="68" rx="6" ${st(W,5)}/><path ${st(W,5)} d="M10 32H90"/>
         <rect x="22" y="44" width="24" height="28" ${st(R,4)}/><path ${st(R,4)} d="M56 46H78M56 58H78M56 70H70"/>`,
  team: `<circle cx="36" cy="36" r="13" ${st(W,5)}/><path ${st(W,5)} d="M12 84C12 66 22 58 36 58C50 58 60 66 60 84"/>
         <circle cx="68" cy="32" r="10" ${st(R,4)}/><path ${st(R,4)} d="M62 56C66 54 70 53 74 53C84 53 90 60 90 76"/>`,
  video: `<rect x="10" y="20" width="80" height="60" rx="8" ${st(W,5)}/><path ${st(R,5)} d="M42 36L64 50L42 64Z"/>`,
  head: `<path ${st(W,5)} d="M34 92V76C20 69 15 54 19 40C24 22 40 11 57 13C75 15 87 30 85 48L91 61L83 63V73C83 80 77 82 71 80L64 79V92"/>
         <circle cx="57" cy="44" r="10" ${st(W,4)}/><circle cx="57" cy="44" r="3" fill="${W}"/>`,
  network: `<circle cx="50" cy="50" r="12" ${st(W,5)}/><circle cx="18" cy="22" r="7" ${st(R,4)}/><circle cx="84" cy="24" r="7" ${st(R,4)}/>
            <circle cx="20" cy="82" r="7" ${st(R,4)}/><circle cx="82" cy="80" r="7" ${st(R,4)}/>
            <path ${st(W,3.5)} d="M24 27L41 42M78 29L59 42M25 77L41 58M77 75L59 58"/>`,
  magnifier: `<circle cx="42" cy="42" r="26" ${st(W,6)}/><path ${st(W,7)} d="M61 61L86 86"/><path ${st(R,5)} d="M34 34L50 50M50 34L34 50"/>`,
  clock: `<circle cx="50" cy="50" r="36" ${st(W,5)}/><path ${st(R,5)} d="M50 28V50L66 60"/>`,
  chip: `<rect x="26" y="26" width="48" height="48" rx="6" ${st(W,5)}/><text x="50" y="58" text-anchor="middle" font-family="Segoe UI" font-weight="700" font-size="22" fill="${W}">AI</text>
         <path ${st(W,4)} d="M38 26V12M50 26V12M62 26V12M38 74V88M50 74V88M62 74V88M26 38H12M26 50H12M26 62H12M74 38H88M74 50H88M74 62H88"/>
         <circle cx="38" cy="10" r="3" fill="${R}"/><circle cx="62" cy="90" r="3" fill="${R}"/><circle cx="10" cy="50" r="3" fill="${R}"/><circle cx="90" cy="38" r="3" fill="${R}"/>`,
  // ---- added for the chapters ----
  pen: `<path ${st(W,5)} d="M24 76L30 56L64 22L78 36L44 70Z"/><path ${st(W,5)} d="M58 28L72 42"/><path ${st(R,5)} d="M18 88H54"/>`,
  grid: `<rect x="14" y="14" width="30" height="30" rx="5" ${st(W,5)}/><rect x="56" y="14" width="30" height="30" rx="5" ${st(W,5)}/>
         <rect x="14" y="56" width="30" height="30" rx="5" ${st(W,5)}/><rect x="56" y="56" width="30" height="30" rx="5" ${st(R,5)}/>`,
  share: `<circle cx="26" cy="50" r="10" ${st(W,5)}/><circle cx="74" cy="24" r="10" ${st(R,5)}/><circle cx="74" cy="76" r="10" ${st(R,5)}/>
          <path ${st(W,4)} d="M35 45L65 29M35 55L65 71"/>`,
  shield: `<path ${st(W,5)} d="M50 10L82 22V46C82 68 68 82 50 90C32 82 18 68 18 46V22Z"/><path ${st(R,5)} d="M35 49L46 60L66 39"/>`,
  reuse: `<path ${st(W,5)} d="M22 52A28 28 0 0 1 72 30"/><path ${st(W,5)} d="M74 16V32H58"/>
          <path ${st(R,5)} d="M78 48A28 28 0 0 1 28 70"/><path ${st(R,5)} d="M26 84V68H42"/>`,
  person: `<circle cx="50" cy="32" r="16" ${st(W,5)}/><path ${st(W,5)} d="M20 88C20 66 33 56 50 56C67 56 80 66 80 88"/><circle cx="50" cy="32" r="4" fill="${R}"/>`,
  building: `<rect x="20" y="20" width="44" height="68" rx="3" ${st(W,5)}/><path ${st(W,5)} d="M64 44H82V88H64"/>
             <path ${st(R,5)} d="M32 34H52M32 50H52M32 66H52"/><path ${st(W,5)} d="M12 88H90"/>`,
  target: `<circle cx="50" cy="50" r="36" ${st(W,5)}/><circle cx="50" cy="50" r="20" ${st(W,5)}/><circle cx="50" cy="50" r="6" fill="${R}"/>`,
  rocket: `<path ${st(W,5)} d="M50 10C66 22 72 42 66 64H34C28 42 34 22 50 10Z"/><circle cx="50" cy="38" r="7" ${st(R,4)}/>
           <path ${st(W,5)} d="M34 64L22 78L36 76M66 64L78 78L64 76"/><path ${st(R,5)} d="M44 76V88M56 76V88"/>`,
  layers: `<path ${st(W,5)} d="M50 14L88 34L50 54L12 34Z"/><path ${st(W,5)} d="M12 50L50 70L88 50"/><path ${st(R,5)} d="M12 66L50 86L88 66"/>`,
  bolt: `<path ${st(W,5)} d="M56 10L22 56H48L42 90L78 42H52Z"/><circle cx="80" cy="18" r="4" fill="${R}"/>`,
};

const el = (tag, attrs, parent) => {
  const e = document.createElementNS(SVGNS, tag);
  for (const k in attrs) if (attrs[k] !== undefined && attrs[k] !== null) e.setAttribute(k, attrs[k]);
  parent && parent.appendChild(e);
  return e;
};
const div = (cls, text, style, parent, data) => {
  const d = document.createElement("div");
  d.className = cls;
  if (text !== undefined) d.innerHTML = text;
  Object.assign(d.style, style || {});
  for (const k in (data || {})) d.dataset[k] = data[k];
  parent && parent.appendChild(d);
  return d;
};
function placeIcons(root) {
  root.querySelectorAll("[data-icon]").forEach(g => {
    const s = +g.dataset.s, x = +g.dataset.x, y = +g.dataset.y;
    let svg = ICONS[g.dataset.icon];
    if (!svg) throw new Error("unknown icon " + g.dataset.icon);
    if (g.dataset.on === "red") svg = svg.split(R).join(W);
    g.innerHTML = `<g transform="translate(${x - s / 2},${y - s / 2}) scale(${s / 100})" filter="url(#glowSoft)">${svg}</g>`;
  });
}

// ---------- building helpers for chapter pages ----------
// node: circle (+ optional icon) in an svg group, optional label div in a html container
function node(svg, html, o) {
  const g = el("g", { class: "a" + (o.breathe ? " breathe" : "") + (o.drift != null ? " drift" : ""), "data-at": o.at, "data-k": o.drift, "data-out": o.out }, svg);
  el("circle", { cx: o.x, cy: o.y, r: o.r || 60, fill: o.fill || PURPLE, stroke: o.stroke || "rgba(255,255,255,.35)",
    "stroke-width": o.strokeW || 2, filter: o.glow ? "url(#glowRed)" : null, opacity: o.opacity }, g);
  if (o.icon) el("g", { "data-icon": o.icon, "data-x": o.x, "data-y": o.y, "data-s": o.iconSize || (o.r || 60) * 1.2,
    "data-on": o.fill === R ? "red" : null }, g);
  if (o.text) {
    const t = el("text", { x: o.x, y: o.y + (o.textSize || 40) * 0.35, "text-anchor": "middle", class: "svgtext",
      "font-size": o.textSize || 40 }, g);
    t.textContent = o.text;
  }
  if (o.label && html) {
    const above = o.labelPos === "above";
    const gap = o.labelGap != null ? o.labelGap : 14;
    const ly = above ? o.y - (o.r || 60) - 38 - gap : o.y + (o.r || 60) + gap;
    div("nlabel a" + (o.drift != null ? " drift" : ""), o.label, { left: o.x + "px", top: ly + "px" }, html,
      Object.assign({ at: o.labelAt || o.at, k: o.drift != null ? o.drift : "" }, o.out ? { out: o.labelOut || o.out } : {}));
  }
  return g;
}
function pill(html, o) {
  const cls = "pill a" + (o.sm ? " sm" : "") + (o.red ? " red" : "") + (o.left ? " left" : "");
  const text = (o.dot ? '<span class="dot"></span>' : "") + o.text;
  return div(cls, text, { left: o.x + "px", top: o.y + "px", width: o.w ? o.w + "px" : null }, html,
    Object.assign({ at: o.at }, o.out ? { out: o.out } : {}));
}
function line(svg, o) {
  return el("line", { x1: o.x1, y1: o.y1, x2: o.x2, y2: o.y2, stroke: o.stroke || "rgba(255,255,255,.8)",
    "stroke-width": o.w || 2.5, pathLength: 1, class: "draw", "data-at": o.at, "data-dur": o.dur }, svg);
}
// thin red bracket with dots at both ends (groups a column of pills)
function bracket(svg, o) {
  line(svg, { x1: o.x, y1: o.y1, x2: o.x, y2: o.y2, stroke: R, w: 2.5, at: o.at, dur: o.dur || 0.9 });
  el("circle", { cx: o.x, cy: o.y1, r: 6, fill: R, class: "a", "data-at": o.at }, svg);
  el("circle", { cx: o.x, cy: o.y2, r: 6, fill: R, class: "a", "data-at": o.endAt || o.at + "+0.6" }, svg);
}

const builders = [];
const ENGINE_DIR = document.currentScript.src.replace(/[^/]*$/, "");   // engine/ folder, so shared assets resolve from any video's page
window.ENGINE = { TL, R, W, PURPLE, BLUE, ICONS, el, div, node, pill, line, bracket, build: f => builders.push(f), start };

// ---------- chrome injected into every page ----------
function injectChrome(stage) {
  stage.insertAdjacentHTML("afterbegin",
    '<div id="bg"><canvas id="particles" width="1920" height="1080"></canvas></div><div id="vignette"></div>' +
    '<div id="label">KNOWLEDGE MANAGEMENT</div><img id="corner" src="' + ENGINE_DIR + 'assets/lenovo.png" alt="">');
  stage.insertAdjacentHTML("beforeend",
    `<svg width="0" height="0" style="position:absolute"><defs>
      <filter id="glowRed" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="22" result="b"/>
        <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      <filter id="glowSoft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="8" result="b"/>
        <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      <filter id="glowDot" x="-400%" y="-400%" width="900%" height="900%"><feGaussianBlur stdDeviation="7" result="b"/>
        <feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    </defs></svg>
    <div id="subs"><div class="zh"></div><div class="en"></div></div><div id="fade"></div>`);
}

// ---------- background ----------
const STRIPES = [], P = [];
let pctx;
function buildBg() {
  const bg = document.getElementById("bg");
  let seed = 3;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  [{ x: 1350, y: 250, s: 900, c: "rgba(233,58,58,.30)" }, { x: 350, y: 700, s: 1000, c: "rgba(61,30,109,.75)" },
   { x: 1600, y: 900, s: 700, c: "rgba(61,30,109,.55)" }].forEach(g => {
    const d = document.createElement("div");
    d.className = "glow";
    Object.assign(d.style, { left: g.x - g.s / 2 + "px", top: g.y - g.s / 2 + "px", width: g.s + "px", height: g.s + "px", background: g.c });
    bg.insertBefore(d, bg.firstChild);
  });
  for (let i = 0; i < 16; i++) {
    const d = document.createElement("div");
    d.className = "stripe";
    const w = 50 + rnd() * 150, x = i * 125 + rnd() * 60 - 40;
    const red = rnd() < 0.35;
    const c = red ? `rgba(160,40,90,${0.25 + rnd() * 0.2})` : `rgba(${80 + rnd() * 40 | 0},${40 + rnd() * 25 | 0},${130 + rnd() * 50 | 0},${0.22 + rnd() * 0.25})`;
    d.style.width = w + "px";
    d.style.background = `linear-gradient(180deg, rgba(0,0,0,0), ${c} 30%, ${c} 70%, rgba(0,0,0,0))`;
    bg.insertBefore(d, document.getElementById("particles"));
    STRIPES.push({ d, x, ph: rnd() * 6.28, sp: 0.12 + rnd() * 0.18, amp: 25 + rnd() * 45 });
  }
  seed = 11;
  for (let i = 0; i < 90; i++) P.push({ x: rnd() * 1920, y: rnd() * 1080, r: 0.8 + rnd() * 2.2, v: 4 + rnd() * 14, ph: rnd() * 6.28, red: rnd() < 0.25 });
  pctx = document.getElementById("particles").getContext("2d");
}
function renderBg(t) {
  STRIPES.forEach(s => { s.d.style.transform = `translateX(${s.x + Math.sin(t * s.sp + s.ph) * s.amp}px)`; });
  pctx.clearRect(0, 0, 1920, 1080);
  P.forEach(p => {
    const y = ((p.y - t * p.v) % 1080 + 1080) % 1080;
    const a = 0.25 + 0.35 * (0.5 + 0.5 * Math.sin(t * 1.3 + p.ph));
    pctx.beginPath();
    pctx.arc(p.x + Math.sin(t * 0.3 + p.ph) * 12, y, p.r, 0, 6.283);
    pctx.fillStyle = p.red ? `rgba(233,58,58,${a})` : `rgba(255,255,255,${a})`;
    pctx.fill();
  });
}

// ---------- timeline helpers ----------
const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const easeOut = p => 1 - Math.pow(1 - p, 3);
const easeInOut = p => p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
const easeOutBack = p => { const c = 1.1; return 1 + (c + 1) * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2); };
const slideOf = id => TL.slides.find(s => s.id === id);
function resolveAt(spec, scene) {
  const m = /^(?:(s)|u(\d+)(?:@([A-Za-z'-]+))?|p(\d+))(?:f([\d.]+))?((?:[+-][\d.]+)*)$/.exec(spec);
  if (!m) throw new Error("bad data-at " + spec);
  let t;
  if (m[1]) t = scene.start;
  else {
    const u = m[2] !== undefined ? TL.units[+m[2]] : TL.subs[+m[4]];
    if (!u) throw new Error("data-at out of range " + spec);
    if (m[3]) {
      const w = (u.words || []).find(([, x]) => x.toLowerCase() === m[3].toLowerCase());
      if (!w) throw new Error(`word "${m[3]}" not spoken in ${spec}`);
      t = w[0];
    } else t = u.start + (m[5] ? (u.end - u.start) * +m[5] : 0);
  }
  return t + (m[6].match(/[+-][\d.]+/g) || []).reduce((a, b) => a + +b, 0);
}
const RAIL = { x: 120, y1: 230, y2: 870 };
// chapters: title appears together with the content and stays at the top ~3 s before docking
// docked title: vertical, centered on the red rail (its midpoint y = 550)
const DOCK = { x: 56, cy: 550, scale: 0.55, dur: 1.0, lead: -2.8 };
const EDGE_FADE = 0.4;   // section starts from black / ends to black

let SCENES = [], zhEl, enEl, subsEl, fadeEl;
function start() {
  const stage = document.getElementById("stage");
  injectChrome(stage);
  builders.forEach(f => f());
  placeIcons(document);
  buildBg();
  document.querySelectorAll(".scene h1").forEach(h => {
    const svg = el("svg", { class: "art", viewBox: "0 0 1920 1080" });
    el("line", { x1: RAIL.x, y1: RAIL.y1, x2: RAIL.x, y2: RAIL.y2, stroke: R, "stroke-width": 2.5, pathLength: 1,
      class: "draw", "data-at": "s+0.3", "data-dur": "0.9" }, svg);
    el("circle", { cx: RAIL.x, cy: RAIL.y1, r: 7, fill: R, class: "a", "data-at": "s+0.3" }, svg);
    el("circle", { cx: RAIL.x, cy: RAIL.y2, r: 7, fill: R, class: "a", "data-at": "s+1.1" }, svg);
    h.after(svg);
  });
  SCENES = [...document.querySelectorAll(".scene")].map(sc => {
    const s = slideOf(sc.id);
    if (!s) throw new Error("no timeline slide for " + sc.id);
    const first = TL.units.find(u => u.slide === sc.id);
    const anims = [...sc.querySelectorAll("[data-at]")].map(e => ({
      e, at: resolveAt(e.dataset.at, s), dur: +(e.dataset.dur || 0.6),
      kind: e.classList.contains("draw") ? "draw" : e.classList.contains("grow") ? "grow" :
        e.classList.contains("stream") ? "stream" : e.classList.contains("travel") ? "travel" :
        e.classList.contains("pulse") ? "pulse" : (e.dataset.kind || "pop"),
      path: e.dataset.path ? document.getElementById(e.dataset.path) : null,
      drift: e.classList.contains("drift") && e.dataset.k !== "" ? +e.dataset.k : null,
      breathe: e.classList.contains("breathe"), wander: e.classList.contains("wander"),
      dockAt: e.dataset.kind === "dock" ? first.start - DOCK.lead : null,
      out: e.dataset.out ? resolveAt(e.dataset.out, s) : null,
    }));
    const spins = [...sc.querySelectorAll(".spin,.spinr")];
    spins.forEach(c => { c.style.transformBox = "fill-box"; c.style.transformOrigin = "center"; });
    return { sc, s, anims, spins };
  });
  zhEl = document.querySelector("#subs .zh"); enEl = document.querySelector("#subs .en");
  subsEl = document.getElementById("subs"); fadeEl = document.getElementById("fade");
  window.DURATION = TL.duration;
  ENGINE.DOCK = DOCK;
  ENGINE.dockAt = Object.fromEntries(SCENES.flatMap(S => S.anims.filter(A => A.kind === "dock").map(A => [S.sc.id, A.dockAt])));
  window.renderAt(0);
  if (location.search.includes("play")) {
    const t0 = performance.now();
    (function loop() { window.renderAt((performance.now() - t0) / 1000 % TL.duration); requestAnimationFrame(loop); })();
  }
}

function renderScene(S, t) {
  const { sc, s } = S;
  const fin = s.start === 0 ? 1 : clamp((t - s.start) / 0.5), fout = clamp((s.end - t) / 0.4);
  const vis = Math.min(fin, fout);
  sc.style.opacity = vis;
  if (vis <= 0) return;
  S.spins.forEach(c => {
    c.style.transform = `rotate(${(c.classList.contains("spinr") ? -1 : 1) * t * 14}deg)`;
  });
  for (const A of S.anims) {
    const p = clamp((t - A.at) / A.dur), q = easeOut(p);
    const e = A.e;
    if (A.kind === "draw") {
      e.style.strokeDasharray = "1";
      e.style.strokeDashoffset = String(1 - q);
      e.style.opacity = p > 0 ? 1 : 0;
    } else if (A.kind === "grow") {
      e.style.transform = `scaleX(${q * +e.dataset.to})`;
    } else if (A.kind === "stream") {
      e.style.opacity = q;
      e.style.strokeDashoffset = String(-(t - A.at) * 0.35);
    } else if (A.kind === "dock") {
      const pp = clamp((t - A.dockAt) / DOCK.dur);
      if (pp < 0.5) {
        const d1 = easeInOut(pp / 0.5);
        e.style.transform = `translate(${-60 * d1}px, ${(1 - q) * 18}px) scale(${1 - 0.2 * d1})`;
        e.style.opacity = q * (1 - d1);
      } else {
        const d2 = easeOut(clamp((pp - 0.55) / 0.45));
        const bottom = DOCK.cy + e.offsetWidth * DOCK.scale / 2;   // rotated -90deg: the text runs upward from here
        const dx = DOCK.x - e.offsetLeft, dy = bottom - e.offsetTop + (1 - d2) * 40;
        e.style.transform = `translate(${dx}px, ${dy}px) rotate(-90deg) scale(${DOCK.scale})`;
        e.style.opacity = d2;
      }
    } else if (A.kind === "zoom") {
      // camera pull-back: move + scale a whole group around its origin (fixed chrome is outside the group)
      const [dx, dy, sc] = e.dataset.zoom.split(",").map(Number), d = easeInOut(p);
      if (!A.origin) { A.origin = true; e.style.transformOrigin = e.dataset.origin.split(",").map(v => v + "px").join(" ");
        if (e instanceof SVGElement) e.style.transformBox = "view-box"; }
      e.style.transform = `translate(${dx * d}px, ${dy * d}px) scale(${1 + (sc - 1) * d})`;
    } else if (A.kind === "travel") {
      const L = A.path.getTotalLength(), pt = A.path.getPointAtLength(L * easeInOut(p));
      e.setAttribute("cx", pt.x); e.setAttribute("cy", pt.y);
      e.style.opacity = p <= 0 || p >= 1 ? 0 : Math.min(1, p / 0.08, (1 - p) / 0.08);
    } else if (A.kind === "pulse") {
      const r0 = +e.dataset.r0;
      e.setAttribute("r", r0 + 34 * q);
      e.style.opacity = p <= 0 ? 0 : 1 - q;
    } else if (A.kind === "scalex") {
      e.style.opacity = q; e.style.transform = `scaleX(${q})`;
    } else if (A.kind === "bloom") {
      let tf = `scale(${0.12 + 0.88 * easeOutBack(p)})`;
      if (A.breathe) tf += ` scale(${1 + 0.03 * Math.sin(t * 1.6)})`;
      e.style.transform = tf;
      e.style.opacity = clamp(p / 0.15);
    } else if (A.kind === "scaley") {
      e.style.transformOrigin = "center bottom";
      e.style.opacity = clamp(q * 1.5); e.style.transform = `scaleY(${q})`;
    } else if (A.kind === "fadeonly") {
      e.style.opacity = q;
    } else {
      let tf = `translateY(${(1 - q) * 18}px) scale(${0.88 + 0.12 * q})`;
      if (A.breathe) tf += ` scale(${1 + 0.03 * Math.sin(t * 1.6)})`;
      if (A.drift !== null) tf = `translate(${Math.sin(t * 0.6 + A.drift * 1.7) * 6}px, ${Math.cos(t * 0.5 + A.drift) * 6 + (1 - q) * 18}px) scale(${0.88 + 0.12 * q})`;
      if (A.wander) tf += ` translate(${Math.sin(t * 0.9) * 26}px, ${Math.sin(t * 1.4) * 14}px) rotate(${Math.sin(t * 0.9) * 6}deg)`;
      const base = e.classList.contains("nlabel") ? "translateX(-50%) " : "";
      e.style.transform = base + tf;
      e.style.opacity = q * (e.dataset.dim ? +e.dataset.dim : 1) * (A.out === null ? 1 : 1 - clamp((t - A.out) / 0.5));
    }
  }
}

// ---------- subtitles (word-timed parts; a part holds until the next one on the same slide) ----------
let curU = -1;
function renderSubs(t) {
  const U = TL.subs;
  let idx = -1, op = 0;
  for (let i = 0; i < U.length; i++) {
    const u = U[i], next = U[i + 1];
    const hold = next && next.slide === u.slide ? next.start : u.end + 0.35;
    if (t >= u.start && t < hold) {
      idx = i;
      op = Math.min(clamp((t - u.start) / 0.25), clamp((hold - t) / 0.15));
      break;
    }
  }
  if (idx !== curU) {
    curU = idx;
    zhEl.textContent = idx >= 0 ? U[idx].zh : "";
    enEl.textContent = idx >= 0 ? U[idx].en : "";
  }
  subsEl.style.opacity = op;
}

window.renderAt = function (t) {
  renderBg(t);
  SCENES.forEach(S => renderScene(S, t));
  renderSubs(t);
  fadeEl.style.opacity = 1 - Math.min(clamp(t / EDGE_FADE), clamp((TL.duration - t) / EDGE_FADE));
};
})();
