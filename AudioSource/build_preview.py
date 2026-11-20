"""Build AudioSource/preview.html from the files in Assets/Audio + report/metrics.json + build/sfx_meta.json.

Open the page directly from disk (file://). Plain <audio> elements, no server needed.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
AUD = ROOT / "Assets" / "Audio"

# recommended mixer group levels (dB) - mirrored in Docs/SOUND_LOG.md
GROUPS = {"BGM": -8, "SFX": 0, "Ambient": -6}

LONG_DESC = {
    "bgm_training": ("밤의 성당 수련장", ""),
    "bgm_boss": ("보스전", ""),
    "bgm_region1": ("1지역 잿빛 성벽", ""),
    "bgm_title": ("타이틀", ""),
    "amb_rampart": ("성벽 위", ""),
    "amb_tower": ("무너진 망루", ""),
    "amb_cloister": ("회랑 앰비언스", ""),
}
LONG_DESC_FILE = HERE / "build" / "long_meta.json"   # written by make_bgm.py / make_amb.py
LOOPS = {"bgm_training", "bgm_boss", "bgm_region1", "bgm_title", "amb_cloister", "amb_rampart", "amb_tower", "sfx_charge_loop", "sfx_boss_charge_loop"}

# card sections: (title, prefixes in display order)
SECTIONS = [
    ("타격", "약 < 강 < 마무리 순서. 처형·자세 붕괴 포함", ["sfx_hit_light", "sfx_hit_heavy", "sfx_hit_finisher", "sfx_plunge",
                                                     "sfx_execute", "sfx_poise_break"]),
    ("휘두르기 · 대쉬 · 회피 · 이동 · 검 뽑기/넣기", "", ["sfx_sword", "sfx_swing_0", "sfx_swing_heavy", "sfx_dash", "sfx_dodge", "sfx_glide", "sfx_perfect_dodge", "sfx_step",
                              "sfx_jump", "sfx_land"]),
    ("차지", "", ["sfx_charge"]),
    ("적 · 허수아비 · 피격", "", ["sfx_enemy", "sfx_dummy", "sfx_player_hurt"]),
    ("1지역 잿빛 성벽 (v1.2)", "방패병·석궁병·제단·전투방", ["sfx_shield_block", "sfx_bolt", "sfx_kick", "sfx_altar",
                                                     "sfx_gate", "sfx_wave_clear"]),
    ("보스 철벽 · 유물 (v1.2)", "", ["sfx_boss", "sfx_corrupt", "sfx_spike", "sfx_pillar", "sfx_parry", "sfx_relic", "sfx_ui_equip"]),
    ("패리 반격 · 서약 계승", "시간 정지 → 9연 참격 → 폭발 / 클리어 배너", ["sfx_time", "sfx_riposte", "sfx_oath"]),
    ("바탕 시스템", "루멘 · 성수병 · 영혼의 수정", ["sfx_lumen", "sfx_flask", "sfx_soul"]),
    ("1-2 무너진 망루", "침식 사냥개 · 무너지는 발판", ["sfx_hound", "sfx_crumble"]),
    ("UI", "", ["sfx_ui"]),
]


def main():
    metrics = json.loads((HERE / "report" / "metrics.json").read_text(encoding="utf-8"))
    sfx_meta = json.loads((HERE / "build" / "sfx_meta.json").read_text(encoding="utf-8"))
    long_meta = json.loads(LONG_DESC_FILE.read_text(encoding="utf-8")) if LONG_DESC_FILE.exists() else {}
    items = []
    for f in sorted(AUD.rglob("*")):
        if f.suffix.lower() not in (".wav", ".ogg"):
            continue
        name = f.stem
        cat = f.parent.name
        m = metrics.get(name, {})
        sm = sfx_meta.get(name, {})
        if cat == "SFX":
            title, desc = "", sm.get("desc", "")
        else:
            title, desc = LONG_DESC.get(name, ("", ""))
            desc = long_meta.get(name, {}).get("desc", desc)
        items.append({
            "name": name, "cat": cat, "src": "../" + str(f.relative_to(ROOT)).replace("\\", "/"),
            "title": title, "desc": desc, "loop": name in LOOPS,
            "dur": m.get("dur_s"), "tp": m.get("true_peak_dbtp"), "lufs_i": m.get("lufs_i"),
            "lufs_m": m.get("lufs_m_max"), "ch": m.get("channels"), "peak_ms": sm.get("peak_ms", 0),
            "ev": {k: v for k, v in sm.items() if k.endswith("_s")},
        })
    reports = sorted(p.name for p in (HERE / "report").glob("*.png"))
    sections = [{"title": t, "sub": s, "prefixes": p} for t, s, p in SECTIONS]
    html = TEMPLATE.replace("__DATA__", json.dumps(items, ensure_ascii=False)) \
        .replace("__GROUPS__", json.dumps(GROUPS)) \
        .replace("__SECTIONS__", json.dumps(sections, ensure_ascii=False)) \
        .replace("__REPORTS__", json.dumps(reports))
    (HERE / "preview.html").write_text(html, encoding="utf-8")
    print("preview.html:", len(items), "sounds")


TEMPLATE = r"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>일곱 서약 사운드</title>
<style>
:root{
  --bg:#110e18; --panel:#1c1826; --panel2:#2a2536; --line:#3a3448; --text:#dedae4; --muted:#9d97a8;
  --crystal:#56b0ff; --crystal2:#95d6ff; --gold:#dcaa48; --crimson:#e8343f; --onaccent:#0b1f3d;
}
@media (prefers-color-scheme: light){
  :root:not([data-theme="dark"]){
    --bg:#f4f2f8; --panel:#ffffff; --panel2:#ebe8f0; --line:#bfbac8; --text:#1c1826; --muted:#4d475c;
    --crystal:#1d5ba8; --crystal2:#133a6e; --gold:#6e4c1d; --crimson:#b0182f; --onaccent:#ffffff;
  }
}
:root[data-theme="dark"]{
  --bg:#110e18; --panel:#1c1826; --panel2:#2a2536; --line:#3a3448; --text:#dedae4; --muted:#9d97a8;
  --crystal:#56b0ff; --crystal2:#95d6ff; --gold:#dcaa48; --crimson:#e8343f; --onaccent:#0b1f3d;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:14px/1.55 "Segoe UI","Malgun Gothic",system-ui,sans-serif}
header{padding:22px 16px 6px;max-width:1120px;margin:auto}
h1{margin:0;font-size:22px;letter-spacing:.3px}
h1 small{color:var(--muted);font-weight:400;font-size:13px;margin-left:8px}
.lead{color:var(--muted);margin:6px 0 0;max-width:820px}
main{max-width:1120px;margin:auto;padding:0 16px 48px}
.bar{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line);padding:10px 0;display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center}
.bar label{display:flex;gap:6px;align-items:center;color:var(--muted);font-size:13px}
.bar input[type=range]{width:110px;accent-color:var(--crystal)}
.bar output{min-width:44px;color:var(--text);font-variant-numeric:tabular-nums}
button{font:inherit;border:1px solid var(--line);background:var(--panel2);color:var(--text);border-radius:6px;padding:5px 10px;cursor:pointer}
button:hover{border-color:var(--crystal)}
button.on{background:var(--crystal);color:var(--onaccent);border-color:var(--crystal)}
button.stop{border-color:var(--crimson);color:var(--crimson)}
button.good.sel{background:var(--crystal);color:var(--onaccent);border-color:var(--crystal)}
button.fix.sel{background:var(--crimson);color:#fff;border-color:var(--crimson)}
h2{font-size:16px;margin:28px 0 8px;display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
h2 span{color:var(--muted);font-size:12px;font-weight:400}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:10px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 12px;display:flex;flex-direction:column;gap:6px;min-width:0}
.card.playing{border-color:var(--crystal)}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.name{font-family:Consolas,monospace;font-size:13px;font-weight:600;word-break:break-all}
.tag{font-size:11px;padding:1px 6px;border-radius:10px;border:1px solid var(--line);color:var(--muted)}
.tag.loop{color:var(--crystal);border-color:var(--crystal)}
.desc{color:var(--muted);font-size:12.5px}
.meta{font-size:11.5px;color:var(--muted);font-variant-numeric:tabular-nums}
.fb{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
.fb input{flex:1;min-width:120px;font:inherit;font-size:12.5px;background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:4px 8px}
.tests{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:10px}
.test{background:var(--panel2);border:1px dashed var(--line);border-radius:8px;padding:10px 12px}
.test p{margin:4px 0 8px;color:var(--muted);font-size:12.5px}
.test.disabled{opacity:.5}
progress{width:100%;height:6px;accent-color:var(--crystal)}
.reports{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px}
.reports a{display:block;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:6px;color:var(--muted);font-size:12px;text-decoration:none}
.reports img{width:100%;display:block;border-radius:4px;margin-bottom:4px;background:#000}
#fbOut{width:100%;min-height:90px;font:12.5px/1.5 Consolas,monospace;background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:8px;padding:8px;display:none;margin-top:8px}
</style>
</head>
<body>
<header>
  <h1>일곱 서약 — 사운드 미리듣기 <small>전부 코드로 합성 · 44.1kHz 16-bit</small></h1>
  <p class="lead">카드의 ▶로 하나씩, 아래 <b>시뮬레이션</b>으로 실제 전투 박자대로 겹쳐 들어보세요(GDD 프레임 데이터·히트스톱 반영).
  카드마다 <b>좋음 / 고쳐줘 + 메모</b>를 남기고 맨 위 <b>피드백 복사</b>를 누르면 채팅에 붙여넣을 글이 만들어집니다.</p>
</header>
<main>
  <div class="bar">
    <label>BGM <input type="range" min="-30" max="6" step="1" data-g="BGM"><output></output></label>
    <label>SFX <input type="range" min="-30" max="6" step="1" data-g="SFX"><output></output></label>
    <label>앰비언스 <input type="range" min="-30" max="6" step="1" data-g="Ambient"><output></output></label>
    <button class="stop" id="stopAll">■ 전부 정지</button>
    <button id="fbCopy">피드백 복사</button>
  </div>
  <textarea id="fbOut" readonly></textarea>

  <h2>시뮬레이션 <span>휘두르기는 '휘익 정점'이 타격 프레임보다 살짝 앞에 오도록 맞춰 재생</span></h2>
  <div class="tests" id="tests"></div>

  <div id="lists"></div>

  <h2>측정 리포트 <span>AudioSource/report/*.png · 가로선 = 5 kHz / 10 kHz</span></h2>
  <div class="reports" id="reports"></div>
</main>
<script>
const DATA = __DATA__;
const GROUPS = __GROUPS__;
const SECTIONS = __SECTIONS__;
const REPORTS = __REPORTS__;
const GROUP_OF = {SFX:"SFX", BGM:"BGM", Ambient:"Ambient"};
const gainDb = Object.assign({}, GROUPS);
const live = new Set();
const lin = db => Math.pow(10, db/20);
const vol = (cat, extraDb=0) => Math.min(1, lin(gainDb[GROUP_OF[cat]] + extraDb));
const byName = Object.fromEntries(DATA.map(d => [d.name, d]));
const F = 1000/60;  // one frame in ms
function fmt(v, d=1){ return (v===null||v===undefined) ? "–" : Number(v).toFixed(d); }

// preload every clip once so simulation timing is tight
const tmpl = {};
for (const d of DATA){ const a = new Audio(); a.preload = d.cat === "SFX" ? "auto" : "none"; a.src = d.src; tmpl[d.name] = a; }

function playOnce(name, extraDb=0, rate=1){
  const d = byName[name]; if(!d) return null;
  const a = tmpl[name].cloneNode(); a.volume = vol(d.cat, extraDb); a.playbackRate = rate;
  a.preservesPitch = false; a.mozPreservesPitch = false; a.webkitPreservesPitch = false;
  a.dataset.cat = d.cat; a.dataset.extra = extraDb; live.add(a); a.onended = () => live.delete(a); a.play().catch(()=>{}); return a;
}
const timers = new Set();
function later(ms, fn){ const t = setTimeout(() => { timers.delete(t); fn(); }, ms); timers.add(t); return t; }
function stopAll(){
  timers.forEach(clearTimeout); timers.clear();
  live.forEach(a => { a.pause(); }); live.clear();
  document.querySelectorAll(".card.playing").forEach(c => c.classList.remove("playing"));
  document.querySelectorAll("button.on").forEach(b => { b.classList.remove("on"); if(b.dataset.label) b.textContent = b.dataset.label; });
  Object.values(TESTS).forEach(t => t.running = false);
}
document.getElementById("stopAll").onclick = stopAll;
document.querySelectorAll(".bar input[type=range]").forEach(r => {
  const g = r.dataset.g; r.value = gainDb[g]; const o = r.nextElementSibling; o.textContent = r.value + " dB";
  r.oninput = () => { gainDb[g] = +r.value; o.textContent = r.value + " dB";
    live.forEach(a => { if (GROUP_OF[a.dataset.cat] === g) a.volume = vol(a.dataset.cat, +(a.dataset.extra||0)); }); };
});

// ---------- feedback (kept in this browser only)
const FB_KEY = "sevenoaths.sound.fb";
let fb = {}; try { fb = JSON.parse(localStorage.getItem(FB_KEY) || "{}"); } catch(e) { fb = {}; }
function saveFb(){ try { localStorage.setItem(FB_KEY, JSON.stringify(fb)); } catch(e) {} }
document.getElementById("fbCopy").onclick = () => {
  const lines = Object.entries(fb).filter(([n, v]) => v.verdict || v.note)
    .map(([n, v]) => `- ${n}: ${v.verdict === "good" ? "좋음" : v.verdict === "fix" ? "고쳐줘" : "메모"}${v.note ? " — " + v.note : ""}`);
  const text = "[사운드 피드백]\n" + (lines.length ? lines.join("\n") : "(아직 표시한 소리가 없음)");
  const out = document.getElementById("fbOut"); out.style.display = "block"; out.value = text; out.select();
  try { navigator.clipboard.writeText(text); } catch(e) { try { document.execCommand("copy"); } catch(e2) {} }
};

// ---------- cards
const lists = document.getElementById("lists");
function card(d){
  const c = document.createElement("div"); c.className = "card";
  const loud = d.cat === "SFX" ? `LUFS-M ${fmt(d.lufs_m)}` : `LUFS-I ${fmt(d.lufs_i)}`;
  const ev = Object.entries(d.ev||{}).map(([k,v]) => `${k.replace("_s","")} @${Math.round(v*1000)}ms`).join(" · ");
  const pk = (d.cat === "SFX" && d.name.match(/swing|dodge|dash/)) ? ` · 휘익 정점 ${d.peak_ms}ms` : "";
  c.innerHTML = `<div class="row"><span class="name">${d.name}</span>${d.title?`<span class="tag">${d.title}</span>`:""}${d.loop?'<span class="tag loop">루프</span>':""}</div>
    <div class="desc">${d.desc||""}</div>
    <div class="meta">${fmt(d.dur,2)} s · ${d.ch===2?"스테레오":"모노"} · ${loud} · TP ${fmt(d.tp)} dBTP${pk}${ev?" · "+ev:""}</div>`;
  const ctr = document.createElement("div"); ctr.className = "row";
  const audio = new Audio(); audio.preload = "none"; audio.src = d.src; audio.dataset.cat = d.cat;
  const prog = document.createElement("progress"); prog.max = 1; prog.value = 0;
  const b = document.createElement("button"); b.textContent = "▶ 재생"; b.dataset.label = "▶ 재생";
  const reset = () => { b.classList.remove("on"); b.textContent = b.dataset.label; c.classList.remove("playing"); live.delete(audio); };
  b.onclick = () => {
    if (!audio.paused){ audio.pause(); audio.currentTime = 0; reset(); return; }
    audio.loop = d.loop; audio.volume = vol(d.cat); live.add(audio); audio.currentTime = 0; audio.play().catch(()=>{});
    b.classList.add("on"); b.textContent = "■ 정지"; c.classList.add("playing");
  };
  audio.onended = reset; audio.onpause = () => { if (!audio.ended && audio.currentTime === 0) reset(); };
  audio.ontimeupdate = () => { if (audio.duration) prog.value = audio.currentTime / audio.duration; };
  ctr.appendChild(b);
  if (d.loop){
    const s = document.createElement("button"); s.textContent = "↻ 이음새 듣기";
    s.title = "끝 직전부터 재생 → 루프 지점을 넘어 처음으로 이어지는지 확인";
    s.onclick = () => { audio.loop = true; audio.volume = vol(d.cat); live.add(audio);
      const go = () => { audio.currentTime = Math.max(0, audio.duration - Math.min(4, audio.duration*0.5)); audio.play().catch(()=>{}); };
      if (isNaN(audio.duration)) { audio.preload = "auto"; audio.addEventListener("loadedmetadata", go, {once:true}); audio.load(); } else go();
      b.classList.add("on"); b.textContent = "■ 정지"; c.classList.add("playing"); };
    ctr.appendChild(s);
  }
  c.appendChild(ctr); c.appendChild(prog);
  // feedback row
  const f = fb[d.name] || {}; const row = document.createElement("div"); row.className = "fb";
  const g = document.createElement("button"); g.className = "good" + (f.verdict === "good" ? " sel" : ""); g.textContent = "좋음";
  const x = document.createElement("button"); x.className = "fix" + (f.verdict === "fix" ? " sel" : ""); x.textContent = "고쳐줘";
  const note = document.createElement("input"); note.placeholder = "메모 (예: 더 둔탁하게)"; note.value = f.note || "";
  const set = v => { const cur = fb[d.name] || {}; cur.verdict = cur.verdict === v ? "" : v; fb[d.name] = cur; saveFb();
    g.classList.toggle("sel", cur.verdict === "good"); x.classList.toggle("sel", cur.verdict === "fix"); };
  g.onclick = () => set("good"); x.onclick = () => set("fix");
  note.oninput = () => { const cur = fb[d.name] || {}; cur.note = note.value; fb[d.name] = cur; saveFb(); };
  row.append(g, x, note); c.appendChild(row);
  return c;
}
function section(title, sub, rows, folder){
  if (!rows.length) return;
  const h = document.createElement("h2"); h.innerHTML = `${title} <span>${rows.length}개 · ${folder}${sub ? " · " + sub : ""}</span>`; lists.appendChild(h);
  const grid = document.createElement("div"); grid.className = "grid"; lists.appendChild(grid);
  rows.forEach(d => grid.appendChild(card(d)));
}
const used = new Set();
for (const s of SECTIONS){
  const rows = [];
  for (const p of s.prefixes) DATA.filter(d => d.cat === "SFX" && d.name.startsWith(p) && !used.has(d.name)).forEach(d => { rows.push(d); used.add(d.name); });
  section(s.title, s.sub, rows, "Assets/Audio/SFX/");
}
section("기타 효과음", "", DATA.filter(d => d.cat === "SFX" && !used.has(d.name)), "Assets/Audio/SFX/");
section("배경음악", "", DATA.filter(d => d.cat === "BGM"), "Assets/Audio/BGM/");
section("앰비언스", "", DATA.filter(d => d.cat === "Ambient"), "Assets/Audio/Ambient/");

// ---------- combat simulations (times in ms, GDD frames at 60 fps)
const pick = arr => arr[Math.floor(Math.random()*arr.length)];
const names = p => DATA.filter(d => d.name.startsWith(p)).map(d => d.name);
const has = n => !!byName[n];
const rate = () => 0.97 + Math.random()*0.06;           // code plays SFX at pitch +-3 %
const sfx = (n, extra=0) => playOnce(n, extra, rate());
// swing so that its whoosh peak lands 25 ms before the hit frame (never before the move starts)
function swingAt(start, hitT, n){ const pk = (byName[n]||{}).peak_ms || 0; later(Math.max(start, hitT - pk - 25), () => sfx(n)); }
const HS = {light: 4*F, heavy: 8*F, fin: 14*F};
function attack(t, wind, grade, swingName, hitName, extra){
  const hit = t + wind*F; swingAt(t, hit, swingName); later(hit, () => { sfx(hitName); if (extra) extra(); });
  return hit + HS[grade];                              // hit-stop freezes the timeline
}
const L = () => pick(names("sfx_hit_light")), H = () => pick(names("sfx_hit_heavy"));
const SW = () => pick(names("sfx_swing_0")), SWH = () => pick(names("sfx_swing_heavy"));
let bedEls = [];
function bed(list){ bedEls = list.filter(([n]) => has(n)).map(([n, extra]) => { const a = playOnce(n, extra||0); if (a) a.loop = true; return a; }); }
const TESTS = {
  ladder: {t:"타격 등급 비교", p:"약 → 강 → 마무리(차지 2단). 히트스톱 4f / 8f / 14f.", period: 4200, run(){
    let t = 0; t = attack(t, 7, "light", SW(), L()); t += 900;
    t = attack(t, 16, "heavy", SWH(), H()); t += 1100;
    attack(t, 6, "fin", SWH(), "sfx_hit_finisher"); }},
  combo: {t:"3연 베기", p:"베기1(7f) → 16f에 베기2(8f) → 베기3 내려꽂기(v1.3: 큰 휘익 → 착지 땅 충격 + 마무리 타격음). 검 소리는 전부 강철.", period: 2600, run(){
    let s = 0, h;
    h = attack(s, 7, "light", SW(), L()); s = s + 16*F + HS.light;
    h = attack(s, 8, "light", SW(), L()); s = s + 17*F + HS.light;
    later(s + 80, () => sfx(SWH())); later(s + 300, () => { sfx("sfx_plunge_land"); sfx("sfx_hit_finisher"); }); }},
  rhythm: {t:"베고 회피로 끊기", p:"베기1 → 10f 회피 캔슬 → 11f 회피 베기(4f) → 13f 베기2. '한 방 → 회피 → 한 방' 박자.", period: 2400, run(){
    let s = 0;
    attack(s, 7, "light", SW(), L()); s = s + 10*F + HS.light;
    later(s, () => sfx(pick(names("sfx_dodge_"))));  s += 11*F;
    attack(s, 4, "light", SW(), L()); s = s + 13*F + HS.light;
    attack(s, 8, "light", SW(), L()); }},
  execute: {t:"자세 붕괴 → 처형", p:"강공으로 자세 붕괴 → 1초 뒤 처형(파일 시작 = 처형 시작, 0.3초에 꽂힘) → 병사 소멸.", period: 5200, run(){
    let s = 0; s = attack(s, 16, "heavy", SWH(), H(), () => sfx("sfx_poise_break"));
    s += 1000; later(s, () => sfx("sfx_execute"));
    later(s + 300 + 650, () => sfx("sfx_enemy_death")); }},
  charge: {t:"차지 2단 (v0.3 좌클릭 홀드)", p:"베기1(헛스윙) → 18f에 차지 자세(웅웅 시작) → +24f 1단 '칭' → +60f 2단 '칭' → +75f 해방(6f) → 마무리 타격.", period: 4200, run(){
    swingAt(0, 7*F, SW()); const c0 = 18*F; let loop = null;
    later(c0, () => { loop = playOnce("sfx_charge_loop"); if (loop) loop.loop = true; });
    later(c0 + 24*F, () => sfx("sfx_charge_ready_01")); later(c0 + 60*F, () => sfx("sfx_charge_ready_02"));
    const rel = c0 + 75*F; later(rel, () => { if (loop){ loop.pause(); live.delete(loop); } });
    attack(rel, 6, "fin", SWH(), "sfx_hit_finisher"); }},
  dash: {t:"대쉬 공격 (v0.3)", p:"우클릭 대쉬: 5f 예비 → 9f 돌진 중 적 2명 관통(강 타격, 각 8f 히트스톱) → 20f에 베기2 연결.", period: 2600, run(){
    const d = pick(names("sfx_dash")); if (!d) return; sfx(d);
    let s = 5*F + 3*F; later(s, () => sfx(H())); s += HS.heavy + 3*F; later(s, () => sfx(H(), -2)); s += HS.heavy;
    attack(20*F + 2*HS.heavy, 8, "light", SW(), L()); }},
  enemy: {t:"병사와 교전", p:"붉은 번뜩임(예고) → 18f 뒤 내려베기 → 퍼펙트 회피 → 1.5배 반격(강공). 3번째마다 피격.", period: 2600, n:0, run(){
    this.n = (this.n||0) + 1; const hurt = this.n % 3 === 0;
    sfx("sfx_enemy_glint"); const hit = 18*F;
    later(Math.max(0, hit - ((byName["sfx_enemy_swing"]||{}).peak_ms||0)), () => sfx("sfx_enemy_swing"));
    if (hurt){ later(hit, () => sfx(pick(names("sfx_player_hurt")))); return; }
    later(hit - 3*F, () => sfx("sfx_perfect_dodge"));
    attack(hit + 500, 16, "heavy", SWH(), H()); }},
  dummy: {t:"허수아비 연습", p:"허수아비에 베기 1·2와 강공. 나무+짚 소리(타격음 대신).", period: 2200, run(){
    const D = () => pick(names("sfx_dummy_hit"));
    let s = 0; attack(s, 7, "light", SW(), D()); s += 16*F + HS.light;
    attack(s, 8, "light", SW(), D()); s += 26*F + HS.light;
    attack(s, 16, "heavy", SWH(), D(), () => sfx(H(), -8)); }},
  move: {t:"질주 · 점프 · 착지 (v1.3)", p:"낮게 미끄러지는 질주(보폭 0.25초마다 '쉭') → 점프 → 0.65초 체공 → 착지 → 다시 질주.", period: 3600, run(){
    const st = names("sfx_glide"); let s = 0;
    for (let k = 0; k < 6; k++){ later(s, () => sfx(pick(st))); s += 250; }
    later(s, () => sfx("sfx_jump")); s += 650; later(s, () => sfx("sfx_land")); s += 250;
    for (let k = 0; k < 5; k++){ later(s, () => sfx(pick(st))); s += 250; } }},
  sword: {t:"검 뽑기 · 넣기 (v1.1)", p:"검을 넣은 채 → 발도 베기(뽑기 + 바로 베기1) → 2초 가만히 → 넣기 v2(서서 넣기: 동작 시작 0.22초 뒤 재생, 파일 0.10초에 딸깍).", period: 4200, run(){
    const dr = pick(names("sfx_sword_draw")); if (dr) sfx(dr);
    attack(40, 7, "light", SW(), L());
    later(2600 + 220, () => sfx("sfx_sword_sheathe")); }},
  plunge: {t:"베기3 내려꽂기 (v1.3)", p:"빛의 구로 떠올랐다가 수직 낙하: 착지 0.22초 전 큰 휘익 → 착지(땅·돌). 첫 번째는 헛침, 두 번째는 적중(+마무리 타격음 겹침).", period: 4200, run(){
    const W = SWH(); sfx(W); later(220, () => sfx("sfx_plunge_land"));
    later(2100, () => sfx(SWH())); later(2320, () => { sfx("sfx_plunge_land"); sfx("sfx_hit_finisher"); }); }},
  shield: {t:"방패병 (1지역)", p:"정면 베기 2번은 방패에 막힘(쿵+불꽃, 3f 히트스톱) → 대쉬로 꿰뚫어 등 뒤 → 강 타격.", period: 3000, run(){
    const B = () => pick(names("sfx_shield_block")); let s = 0;
    attack(s, 7, "light", SW(), B()); s += 16*F + 3*F;
    attack(s, 8, "light", SW(), B()); s += 26*F + 3*F;
    later(s, () => sfx(pick(names("sfx_dash")))); later(s + 8*F, () => sfx(H())); }},
  crossbow: {t:"석궁병 (1지역)", p:"붉은 조준 30f(삐걱+떨림) → 발사 '퉁' → 화살 비행 → 박힘. 두 번째는 근접해서 발차기.", period: 3600, n:0, run(){
    this.n = (this.n||0) + 1;
    if (this.n % 2){ sfx("sfx_bolt_aim"); later(500, () => sfx("sfx_bolt_shoot")); later(500 + 420, () => { sfx("sfx_bolt_hit"); sfx(pick(names("sfx_player_hurt")), -4); }); }
    else { sfx("sfx_kick"); later(30, () => sfx(pick(names("sfx_player_hurt")), -4)); } }},
  arena: {t:"전투방 (1지역)", p:"입장 → 창살 쾅(0.18초) → 싸움 → 웨이브 클리어 스팅어 → 창살 올라감(2.1초에 철컥) → 제단.", period: 9000, run(){
    sfx("sfx_gate_drop"); let s = 1600;
    for (let k = 0; k < 3; k++){ attack(s, 7, "light", SW(), L()); s += 600; }
    later(s + 300, () => sfx("sfx_enemy_death")); later(s + 1400, () => sfx("sfx_wave_clear"));
    later(s + 3200, () => sfx("sfx_gate_rise")); later(s + 6000, () => sfx("sfx_altar")); }},
  boss: {t:"철벽 보스 패턴", p:"번뜩임(12f) → 장검 내려베기(판정 36f, 소리는 판정 0.30초 전에) → 방패 밀치기 → 패리 '캉' → 돌진 3단계(차징 0.5초 → 붉은 줄 '치잉' → 돌진 루프) → 벽 충돌.", period: 7000, run(){
    later(12*F, () => sfx("sfx_enemy_glint")); later(36*F - 300, () => sfx("sfx_boss_slam"));
    later(2200, () => sfx("sfx_boss_bash"));
    later(3300, () => sfx("sfx_parry"));
    later(3800, () => sfx("sfx_boss_charge_up")); later(4300, () => sfx("sfx_boss_charge_line"));
    let loop = null; later(4650, () => { loop = playOnce("sfx_boss_charge_loop"); if (loop) loop.loop = true; });
    later(5900, () => { if (loop){ loop.pause(); live.delete(loop); } sfx("sfx_boss_wall_hit"); }); }},
  boss2: {t:"철벽 2페이즈 · 최후", p:"포효 → 쇠기둥(24f에 쿵) → 기둥 무너짐 → 마지막 처형 → 쓰러짐 → 유물 획득 → 장착.", period: 14000, run(){
    sfx("sfx_boss_roar"); later(2600, () => sfx("sfx_pillar_rise")); later(5000, () => sfx("sfx_pillar_crumble"));
    later(6600, () => sfx("sfx_execute")); later(7300, () => sfx("sfx_boss_death"));
    later(10600, () => sfx("sfx_relic_get")); later(13000, () => sfx("sfx_ui_equip")); }},
  riposte: {t:"패리 반격", p:"패리 '캉' + 뒤로 미끄러지며 칼끝 긁힘(0.3초 '팅') → 시간 정지(0.12초 '팅') → 0.6초 뒤 좌클릭 → 참격 9번 67ms 간격 '샤샤샤샥' → '쾅' → 시간 재개.", period: 4200, run(){
    sfx("sfx_parry"); sfx("sfx_parry_slide"); later(60, () => sfx("sfx_time_stop"));
    const R = names("sfx_riposte_slash"); const t0 = 700;
    for (let k = 0; k < 9; k++) later(t0 + k*67, () => sfx(pick(R)));
    later(t0 + 9*67, () => sfx("sfx_riposte_blast")); later(t0 + 9*67 + 700, () => sfx("sfx_time_resume")); }},
  bossintro: {t:"보스 첫 대면 · 클리어", p:"철벽 함성(0.95초에 방패 쿵) → 붉은 이름 배너 / … 쓰러짐 → '서약을 이었다' 배너 → 글자가 빨려 듦('칭') → 유물.", period: 13000, run(){
    sfx("sfx_boss_intro_shout"); later(1150, () => sfx("sfx_boss_banner"));
    later(3600, () => sfx("sfx_boss_death")); later(7000, () => sfx("sfx_oath_inherit"));
    later(9400, () => sfx("sfx_oath_absorb")); later(10600, () => sfx("sfx_relic_get")); }},
  bossnew: {t:"철벽 신규 패턴", p:"HP 절반 침식 터짐 → 포효 / 도약 → 착지 지점 고정 → 낙하(0.335초에 끊김) → 착지 내리찍기 / 검 꽂고 균열 → 가시 6개 50ms 간격.", period: 11000, run(){
    sfx("sfx_corrupt_burst"); later(1100, () => sfx("sfx_boss_roar"));
    let s = 4600; later(s, () => sfx("sfx_boss_leap")); later(s + 700, () => sfx("sfx_boss_leap_lock"));
    later(s + 1500, () => sfx("sfx_boss_leap_fall")); later(s + 1500 + 335, () => sfx("sfx_boss_leap_impact"));
    s = 8400; later(s, () => sfx("sfx_spike_crack"));
    const E = names("sfx_spike_erupt"); for (let k = 0; k < 6; k++) later(s + 500 + k*50, () => sfx(pick(E))); }},
  system: {t:"루멘 · 성수병 · 영혼의 수정", p:"적 소멸 → 루멘 6알 60ms 간격(최대 4개 동시) → 성수병 마시기(0.4초 회복) → 빈 병 → 사망 자리에 수정 맺힘 → 베어 부숨(0.6초 해결음).", period: 9000, run(){
    sfx("sfx_enemy_death"); const Lm = names("sfx_lumen_gain");
    for (let k = 0; k < 6; k++) later(500 + k*60, () => sfx(Lm[k % 3]));
    later(1800, () => sfx("sfx_flask_drink")); later(3000, () => sfx("sfx_flask_empty"));
    later(4200, () => sfx("sfx_soul_crystal_form")); later(6300, () => sfx(pick(names("sfx_swing_0")))); later(6400, () => sfx("sfx_soul_crystal_break")); }},
  tower: {t:"1-2 무너진 망루", p:"amb_tower 위에서: 사냥개 3마리 으르렁 → 뛰어들며 물기 → 베기에 깨갱 → 쓰러짐 / 발판에 금 → 부서져 떨어짐.", period: 8000, bedList:[["amb_tower"]], needs:["amb_tower"], run(){
    const G = names("sfx_hound_growl"); sfx(G[0]); later(180, () => sfx(G[1], -3));
    later(700, () => sfx("sfx_hound_bite")); later(1200, () => sfx(pick(names("sfx_player_hurt")), -4));
    attack(1900, 7, "light", SW(), "sfx_hound_yelp"); later(2700, () => sfx("sfx_hound_death"));
    later(4600, () => sfx("sfx_crumble_shake")); later(5500, () => sfx("sfx_crumble_break")); }},
  region: {t:"1지역 인게임 믹스", p:"bgm_region1 + amb_rampart 위에 콤보·방패·석궁이 무작위로. 권장 그룹 볼륨 적용.", period: 3200, needs:["bgm_region1"], bedList:[["bgm_region1"],["amb_rampart"]], run(){
    pick([TESTS.combo, TESTS.shield, TESTS.crossbow, TESTS.rhythm, TESTS.dash]).run(); }},
  mix: {t:"수련장 인게임 믹스", p:"bgm_training + amb_cloister 위에 콤보·회피·처형이 무작위로. 권장 그룹 볼륨 적용.", period: 3000, needs:["bgm_training"], bedList:[["bgm_training"],["amb_cloister"]], run(){
    pick([TESTS.combo, TESTS.rhythm, TESTS.combo, TESTS.dash, TESTS.ladder, TESTS.enemy]).run(); }},
  boss: {t:"보스전 인게임 믹스", p:"bgm_boss 위에 콤보·대쉬·차지 마무리·처형이 무작위로. 권장 그룹 볼륨 적용.", period: 2800, needs:["bgm_boss"], bedList:[["bgm_boss"]], run(){
    pick([TESTS.combo, TESTS.dash, TESTS.rhythm, TESTS.ladder, TESTS.enemy, TESTS.combo]).run(); }},
};
const testsEl = document.getElementById("tests");
for (const [key, T] of Object.entries(TESTS)){
  const ok = !T.needs || T.needs.every(has);
  const div = document.createElement("div"); div.className = "test" + (ok ? "" : " disabled");
  div.innerHTML = `<b>${T.t}</b><p>${T.p}${ok ? "" : " (BGM이 아직 없음)"}</p>`;
  const b = document.createElement("button"); b.textContent = "▶ 반복 재생"; b.dataset.label = b.textContent; b.disabled = !ok;
  b.onclick = () => {
    if (b.classList.contains("on")){ stopAll(); return; }
    stopAll(); T.running = true; b.classList.add("on"); b.textContent = "■ 정지";
    if (T.bedList) bed(T.bedList);
    const loop = () => { if (!T.running) return; T.run(); later(T.period, loop); };
    loop();
  };
  div.appendChild(b); testsEl.appendChild(div);
}

// ---------- reports
const rep = document.getElementById("reports");
for (const r of REPORTS){
  const a = document.createElement("a"); a.href = "report/" + r; a.target = "_blank";
  a.innerHTML = `<img loading="lazy" src="report/${r}" alt="${r}">${r}`; rep.appendChild(a);
}
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
