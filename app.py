from flask import Flask, request, redirect, url_for, flash, render_template_string, jsonify
from pathlib import Path
from datetime import datetime
import sqlite3, random, os
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

app=Flask(__name__); app.secret_key=os.getenv('SECRET_KEY','local-prototype-key')
DB=Path(__file__).with_name('monitoring.db')
FEATURES=['login_failures','requests_per_minute','bytes_sent_mb','outside_hours','new_device','unusual_location','privilege_change','port_scan_events']
# Fit an unsupervised detector to synthetic normal behaviour for an isolated demonstration.
rng=np.random.default_rng(42); n=1500
baseline=np.column_stack([rng.poisson(.25,n),rng.normal(35,12,n).clip(1,100),rng.gamma(2,2,n).clip(0,20),rng.binomial(1,.07,n),rng.binomial(1,.04,n),rng.binomial(1,.03,n),rng.binomial(1,.01,n),rng.poisson(.03,n)])
MODEL=make_pipeline(StandardScaler(),IsolationForest(n_estimators=180,contamination=.06,random_state=42)).fit(baseline)

def conn():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init():
 with conn() as c:
  c.execute('''CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,timestamp TEXT,user TEXT,device TEXT,ip TEXT,event_type TEXT,login_failures INTEGER,requests_per_minute REAL,bytes_sent_mb REAL,outside_hours INTEGER,new_device INTEGER,unusual_location INTEGER,privilege_change INTEGER,port_scan_events INTEGER,score REAL,anomaly INTEGER,severity TEXT,status TEXT)''')
  c.execute('''CREATE TABLE IF NOT EXISTS incidents(id INTEGER PRIMARY KEY,event_id INTEGER,title TEXT,priority TEXT,assignee TEXT,status TEXT,notes TEXT,created TEXT)''')
  if c.execute('SELECT COUNT(*) FROM events').fetchone()[0]==0:
   random.seed(7)
   for i in range(70):
    bad=i%11==0
    r=dict(user=random.choice(['operator01','inspector02','payments03','admin01']),device=random.choice(['TERM-01','GATE-04','PAY-08','SRV-CORE']),ip=f'10.0.{random.randint(1,5)}.{random.randint(2,250)}',event_type=random.choice(['Login','Record access','Payment query','Device activity','Network activity']),login_failures=random.randint(4,10) if bad else random.choice([0,0,0,1]),requests_per_minute=random.uniform(160,280) if bad else random.uniform(10,65),bytes_sent_mb=random.uniform(40,100) if bad else random.uniform(.1,8),outside_hours=int(bad),new_device=int(bad and random.random()>.4),unusual_location=int(bad and random.random()>.4),privilege_change=int(bad and random.random()>.7),port_scan_events=random.randint(3,10) if bad else 0)
    save_event(r)
def analyse(r):
 x=np.array([[r[k] for k in FEATURES]],float); anomaly=int(MODEL.predict(x)[0]==-1); raw=float(-MODEL.score_samples(x)[0]); score=round(min(100,max(0,raw*45)),1)
 severity='Critical' if anomaly and score>=72 else 'High' if anomaly and score>=55 else 'Medium' if anomaly else 'Low'
 return anomaly,score,severity
def save_event(r):
 anomaly,score,severity=analyse(r)
 with conn() as c:
  cur=c.execute('''INSERT INTO events(timestamp,user,device,ip,event_type,login_failures,requests_per_minute,bytes_sent_mb,outside_hours,new_device,unusual_location,privilege_change,port_scan_events,score,anomaly,severity,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(datetime.now().isoformat(timespec='seconds'),r['user'],r['device'],r['ip'],r['event_type'],*[r[k] for k in FEATURES],score,anomaly,severity,'Open' if anomaly else 'Normal'))
  return cur.lastrowid,anomaly,score,severity

# ---------------------------------------------------------------------------
# DESIGN SYSTEM — "RoadSecure SOC" (dark, data-dense, premium)
# Tokens -> semantic aliases -> components. All motion uses transform/opacity
# with a custom cubic-bezier; no banned fonts, icons or generic shadows.
# ---------------------------------------------------------------------------
CSS='''<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
:root{
  /* primitive */
  --c-ink-950:#04070f; --c-ink-900:#070c17; --c-ink-850:#0a1120; --c-ink-800:#0d1628;
  --c-ink-700:#131f36; --c-ink-600:#1a2942;
  --c-slate-100:#eaf0fb; --c-slate-300:#b6c4db; --c-slate-400:#8d9eb9; --c-slate-500:#63758f;
  --c-cyan:#22d3ee; --c-teal:#2dd4bf; --c-green:#34d399; --c-amber:#fbbf24;
  --c-rose:#fb7185; --c-red:#f43f5e; --c-violet:#a78bfa; --c-blue:#60a5fa;
  /* semantic */
  --bg:var(--c-ink-950); --surface:var(--c-ink-850); --surface-2:var(--c-ink-800);
  --line:rgba(148,163,184,.10); --line-2:rgba(148,163,184,.18);
  --text:var(--c-slate-100); --muted:var(--c-slate-400); --dim:var(--c-slate-500);
  --accent:var(--c-cyan); --accent-soft:rgba(34,211,238,.13);
  --ok:var(--c-green); --warn:var(--c-amber); --danger:var(--c-rose);
  --font-display:'Space Grotesk',sans-serif; --font-body:'Plus Jakarta Sans',sans-serif;
  --font-mono:'JetBrains Mono',monospace;
  --r-lg:20px; --r-md:14px; --r-sm:10px;
  --ease:cubic-bezier(.32,.72,0,1);
  --side-w:250px;
}
*,*::before,*::after{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;min-height:100vh;background:var(--bg);color:var(--text);font:400 14px/1.55 var(--font-body);-webkit-font-smoothing:antialiased}
/* ambient background — fixed, GPU-light, pointer-events none */
.bg-field{position:fixed;inset:0;z-index:-2;pointer-events:none;
  background:
    radial-gradient(900px 600px at 82% -8%,rgba(34,211,238,.10),transparent 60%),
    radial-gradient(720px 620px at 8% 108%,rgba(99,102,241,.10),transparent 60%),
    linear-gradient(180deg,#050a14 0%,#04070f 100%);}
.bg-grid{position:fixed;inset:0;z-index:-1;pointer-events:none;opacity:.22;
  background-image:linear-gradient(rgba(148,163,184,.055) 1px,transparent 1px),linear-gradient(90deg,rgba(148,163,184,.055) 1px,transparent 1px);
  background-size:46px 46px;mask-image:radial-gradient(ellipse at 60% 30%,#000 30%,transparent 78%)}
/* sidebar */
.side{position:fixed;inset:0 auto 0 0;width:var(--side-w);z-index:20;display:flex;flex-direction:column;
  padding:26px 16px 20px;background:linear-gradient(180deg,rgba(9,15,27,.96),rgba(6,11,20,.98));
  border-right:1px solid var(--line);backdrop-filter:blur(18px)}
.brand{display:flex;align-items:center;gap:12px;text-decoration:none;color:var(--text);margin:2px 6px 34px}
.brand-mark{width:38px;height:38px;flex:none;display:grid;place-items:center;border-radius:11px;
  background:linear-gradient(145deg,rgba(34,211,238,.22),rgba(45,212,191,.08));
  border:1px solid rgba(34,211,238,.3);box-shadow:inset 0 1px 0 rgba(255,255,255,.12),0 0 24px rgba(34,211,238,.12)}
.brand-mark svg{width:21px;height:21px}
.brand-text{font:700 19px/1 var(--font-display);letter-spacing:-.02em}
.brand-text small{display:block;margin-top:6px;font:600 8.5px/1 var(--font-body);letter-spacing:.19em;color:var(--dim)}
.nav-label{margin:0 14px 11px;font:700 9px/1 var(--font-body);letter-spacing:.2em;color:var(--dim)}
nav{display:grid;gap:5px}
nav a{position:relative;display:flex;align-items:center;gap:13px;padding:12px 14px;border-radius:var(--r-sm);
  color:var(--muted);text-decoration:none;font-weight:600;font-size:13px;
  border:1px solid transparent;transition:color .5s var(--ease),background .5s var(--ease),transform .5s var(--ease),border-color .5s var(--ease)}
nav a svg{width:18px;height:18px;flex:none;opacity:.8}
nav a:hover{color:var(--text);background:rgba(148,163,184,.06);transform:translateX(3px)}
nav a.active{color:var(--text);background:linear-gradient(90deg,rgba(34,211,238,.14),rgba(34,211,238,.02));border-color:rgba(34,211,238,.22)}
nav a.active::before{content:"";position:absolute;left:0;top:22%;height:56%;width:2px;border-radius:2px;background:var(--accent);box-shadow:0 0 12px var(--accent)}
nav a.active svg{opacity:1;color:var(--accent)}
.side-foot{margin-top:auto;padding:16px 14px 2px;border-top:1px solid var(--line)}
.side-status{display:flex;align-items:center;gap:9px;font-size:11px;font-weight:600;color:var(--muted)}
.side-meta{margin-top:8px;font:500 9px/1 var(--font-mono);letter-spacing:.08em;color:var(--dim)}
.dot{position:relative;width:7px;height:7px;border-radius:50%;background:var(--ok);box-shadow:0 0 0 0 rgba(52,211,153,.5)}
.dot::after{content:"";position:absolute;inset:-4px;border-radius:50%;border:1px solid rgba(52,211,153,.5);animation:ping 2.4s var(--ease) infinite}
@keyframes ping{0%{transform:scale(.6);opacity:.9}70%,100%{transform:scale(1.7);opacity:0}}
/* main + topbar */
.main{margin-left:var(--side-w);padding:30px 34px 22px;max-width:1620px}
.topbar{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;margin-bottom:26px}
.crumb small{display:block;font:700 9.5px/1 var(--font-body);letter-spacing:.2em;color:var(--dim);margin-bottom:12px}
h1,h2,h3{font-family:var(--font-display);letter-spacing:-.025em;margin:0}
h1{font-size:29px;font-weight:700;line-height:1.1}
h2{font-size:16px;font-weight:600}
h3{font-size:13px;font-weight:600;color:var(--text)}
.topbar-right{display:flex;align-items:center;gap:14px}
.live{display:flex;align-items:center;gap:9px;padding:8px 13px;border-radius:100px;border:1px solid rgba(52,211,153,.2);
  background:rgba(52,211,153,.06);font:700 9px/1 var(--font-body);letter-spacing:.14em;color:var(--ok)}
.clock{font:500 12px/1 var(--font-mono);color:var(--muted);letter-spacing:.04em}
.muted{color:var(--muted);font-size:12px}
/* surfaces — double bezel */
.card,.panel,.surface{position:relative;border-radius:var(--r-lg);padding:1px;
  background:linear-gradient(160deg,rgba(148,163,184,.18),rgba(148,163,184,.04) 40%,rgba(148,163,184,.10));
  box-shadow:0 20px 50px -30px rgba(0,0,0,.8)}
.card>.inner,.panel>.inner,.surface>.inner{border-radius:calc(var(--r-lg) - 1px);background:linear-gradient(160deg,var(--surface-2),var(--surface));
  box-shadow:inset 0 1px 0 rgba(255,255,255,.045);height:100%}
.card-body,.panel-body{padding:20px 21px}
.panel{margin-bottom:18px}
.panel-head{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:19px 21px 15px;border-bottom:1px solid var(--line)}
.panel-head h2{display:flex;align-items:center;gap:10px}
.panel-head h2 svg{width:16px;height:16px;color:var(--accent)}
/* stat cards */
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:18px}
.stat-top{display:flex;align-items:flex-start;justify-content:space-between;gap:10px}
.stat-label{font:600 10.5px/1.3 var(--font-body);letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.stat-ico{width:34px;height:34px;flex:none;display:grid;place-items:center;border-radius:10px;
  border:1px solid var(--line-2);background:rgba(148,163,184,.05);color:var(--accent)}
.stat-ico svg{width:16px;height:16px}
.stat-val{display:block;margin-top:14px;font:600 33px/1 var(--font-mono);letter-spacing:-.04em;color:var(--text)}
.stat-foot{display:flex;align-items:flex-end;justify-content:space-between;gap:8px;margin-top:12px}
.stat-trend{font-size:10.5px;color:var(--dim)}
.stat-trend b{color:var(--ok);font-weight:600}
.spark{width:78px;height:26px;flex:none;overflow:visible}
.tone-cyan{--tone:var(--c-cyan)} .tone-violet{--tone:var(--c-violet)}
.tone-amber{--tone:var(--c-amber)} .tone-green{--tone:var(--c-green)}
.tone-cyan .stat-ico,.tone-violet .stat-ico,.tone-amber .stat-ico,.tone-green .stat-ico{color:var(--tone);border-color:color-mix(in srgb,var(--tone) 30%,transparent);background:color-mix(in srgb,var(--tone) 10%,transparent)}
/* layout grids */
.grid{display:grid;grid-template-columns:1.45fr 1fr;gap:18px;align-items:start}
/* tables */
.tablewrap{overflow:auto}
table{width:100%;border-collapse:collapse;font-size:12px}
th,td{text-align:left;padding:12px 10px;border-bottom:1px solid var(--line);white-space:nowrap}
th{color:var(--dim);font:700 9px/1 var(--font-body);letter-spacing:.16em;text-transform:uppercase;background:rgba(148,163,184,.025)}
tbody tr{transition:background .4s var(--ease)}
tbody tr:hover{background:rgba(148,163,184,.045)}
tbody tr:last-child td{border-bottom:0}
td .mono,td.id{font-family:var(--font-mono);color:var(--muted);font-size:11px}
td strong{font-weight:600;color:var(--text)}
.stack{display:block;line-height:1.5}
.stack small{color:var(--dim);font-size:10px}
/* pills & statuses */
.pill{display:inline-flex;align-items:center;gap:6px;padding:5px 10px;border-radius:100px;font:700 9.5px/1 var(--font-body);
  letter-spacing:.05em;text-transform:uppercase;border:1px solid transparent}
.pill::before{content:"";width:5px;height:5px;border-radius:50%;background:currentColor}
.critical{color:#fda4af;background:rgba(244,63,94,.11);border-color:rgba(244,63,94,.24)}
.high{color:#fcd34d;background:rgba(251,191,36,.10);border-color:rgba(251,191,36,.22)}
.medium{color:#c4b5fd;background:rgba(167,139,250,.10);border-color:rgba(167,139,250,.22)}
.low{color:#6ee7b7;background:rgba(52,211,153,.10);border-color:rgba(52,211,153,.22)}
.status-pill{display:inline-block;padding:4px 9px;border-radius:7px;font:600 10px/1 var(--font-body);
  color:var(--muted);background:rgba(148,163,184,.08);border:1px solid var(--line-2)}
/* buttons — island architecture */
.btn,button{display:inline-flex;align-items:center;justify-content:center;gap:10px;border:0;cursor:pointer;
  padding:11px 16px;border-radius:100px;text-decoration:none;font:700 11.5px/1 var(--font-body);letter-spacing:.02em;
  background:linear-gradient(135deg,#22d3ee,#06b6d4);color:#04121a;
  box-shadow:0 8px 24px -10px rgba(34,211,238,.6),inset 0 1px 0 rgba(255,255,255,.35);
  transition:transform .55s var(--ease),box-shadow .55s var(--ease)}
.btn:hover,button:hover{transform:translateY(-2px);box-shadow:0 14px 30px -10px rgba(34,211,238,.7),inset 0 1px 0 rgba(255,255,255,.35)}
.btn:active,button:active{transform:scale(.98)}
.btn .ico{display:grid;place-items:center;width:22px;height:22px;border-radius:50%;background:rgba(4,18,26,.14);
  transition:transform .55s var(--ease)}
.btn:hover .ico{transform:translate(2px,-1px) scale(1.06)}
.btn .ico svg{width:12px;height:12px}
.secondary{background:rgba(148,163,184,.07);color:var(--text);border:1px solid var(--line-2);box-shadow:none}
.secondary:hover{background:rgba(148,163,184,.12);box-shadow:none;transform:translateY(-2px)}
.ghost{background:transparent;color:var(--muted);border:1px solid var(--line-2);box-shadow:none;padding:8px 12px}
.ghost:hover{background:rgba(148,163,184,.06);box-shadow:none}
.btn-row{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin-top:18px}
/* filters */
.filters{display:flex;flex-wrap:wrap;gap:6px}
.filters a{padding:7px 14px;border-radius:100px;text-decoration:none;font:600 11px/1 var(--font-body);
  color:var(--muted);border:1px solid var(--line);background:rgba(148,163,184,.04);
  transition:color .5s var(--ease),background .5s var(--ease),transform .5s var(--ease)}
.filters a:hover{color:var(--text);transform:translateY(-1px)}
.filters a.on{color:var(--accent);border-color:rgba(34,211,238,.3);background:var(--accent-soft)}
/* forms */
.form{display:grid;gap:16px;max-width:100%}
.form label{display:grid;gap:7px;font-size:11.5px;font-weight:600;color:var(--muted)}
.form input,.form select,.form textarea,select,input[type=number]{
  width:100%;padding:11px 12px;color:var(--text);background:rgba(4,9,18,.55);
  border:1px solid var(--line-2);border-radius:var(--r-sm);font:500 12.5px/1.4 var(--font-body);
  outline:none;transition:border-color .5s var(--ease),box-shadow .5s var(--ease),background .5s var(--ease)}
.form input:focus,.form select:focus,.form textarea:focus,select:focus{
  border-color:rgba(34,211,238,.55);box-shadow:0 0 0 3px rgba(34,211,238,.10);background:rgba(4,9,18,.8)}
.form textarea{resize:vertical;min-height:92px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.checks{display:grid;grid-template-columns:1fr 1fr;gap:9px}
.checks label{display:flex;align-items:center;gap:10px;padding:11px 13px;border-radius:var(--r-sm);
  border:1px solid var(--line);background:rgba(148,163,184,.035);font-size:11.5px;color:var(--muted);font-weight:600;cursor:pointer;
  transition:border-color .5s var(--ease),background .5s var(--ease)}
.checks label:has(input:checked){border-color:rgba(34,211,238,.35);background:var(--accent-soft);color:var(--text)}
.checks input{accent-color:var(--c-cyan);width:15px;height:15px}
.section-cap{margin:4px 0 2px;font:700 9px/1 var(--font-body);letter-spacing:.18em;text-transform:uppercase;color:var(--dim)}
/* result gauge */
.result{display:grid;place-items:center;gap:18px;text-align:center;padding:8px 0}
.gauge{--gauge-col:var(--c-cyan);--score:0;position:relative;width:158px;height:158px;border-radius:50%;
  background:conic-gradient(var(--gauge-col) calc(var(--score)*1%),rgba(148,163,184,.09) 0);
  display:grid;place-items:center;box-shadow:0 0 44px -14px var(--gauge-col)}
.gauge.critical{--gauge-col:var(--c-red)} .gauge.high{--gauge-col:var(--c-amber)}
.gauge.medium{--gauge-col:var(--c-violet)} .gauge.low{--gauge-col:var(--c-green)}
.gauge::before{content:"";position:absolute;inset:11px;border-radius:50%;background:#0a1120;box-shadow:inset 0 1px 0 rgba(255,255,255,.05)}
.gauge-inner{position:relative;display:grid;gap:2px}
.gauge-inner strong{font:600 34px/1 var(--font-mono);letter-spacing:-.04em}
.gauge-inner small{font:600 9px/1 var(--font-body);letter-spacing:.14em;color:var(--dim)}
.result-lines{display:grid;gap:9px;width:100%;max-width:280px}
.result-line{display:flex;justify-content:space-between;align-items:center;padding:10px 13px;border-radius:var(--r-sm);
  background:rgba(148,163,184,.04);border:1px solid var(--line);font-size:11.5px;color:var(--muted)}
.result-line b{color:var(--text);font-family:var(--font-mono)}
/* eval formulas */
.formulas{display:grid;gap:9px;margin-top:4px}
.formula{display:flex;gap:13px;align-items:flex-start;padding:12px 14px;border-radius:var(--r-sm);
  background:rgba(148,163,184,.035);border:1px solid var(--line)}
.formula .n{width:22px;height:22px;flex:none;display:grid;place-items:center;border-radius:7px;
  font:600 10px/1 var(--font-mono);color:var(--accent);background:var(--accent-soft);border:1px solid rgba(34,211,238,.2)}
.formula code{font:500 11.5px/1.5 var(--font-mono);color:var(--text)}
.formula p{margin:3px 0 0;font-size:11px;color:var(--dim)}
.notice{display:flex;gap:12px;align-items:flex-start;padding:14px 16px;margin:2px 0 18px;border-radius:var(--r-md);
  background:rgba(251,191,36,.06);border:1px solid rgba(251,191,36,.18)}
.notice svg{width:17px;height:17px;flex:none;color:var(--c-amber);margin-top:1px}
.notice b{display:block;font-size:11.5px;color:#fcd34d;margin-bottom:3px}
.notice span{font-size:11.5px;color:var(--muted)}
/* misc */
.flash{display:flex;align-items:center;gap:9px;padding:12px 15px;margin-bottom:16px;border-radius:var(--r-sm);
  background:rgba(52,211,153,.08);border:1px solid rgba(52,211,153,.22);color:#6ee7b7;font-size:12px;font-weight:600;
  animation:rise .7s var(--ease) both}
.footer{margin-top:30px;padding-top:16px;border-top:1px solid var(--line);color:var(--dim);font-size:10px;text-align:center;letter-spacing:.04em}
.tip{padding:12px 14px;border-radius:var(--r-sm);background:rgba(148,163,184,.04);border:1px solid var(--line);font-size:11.5px;color:var(--muted)}
.tip code{font-family:var(--font-mono);color:var(--accent);font-size:11px}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}
.reveal{animation:rise .8s var(--ease) both}
.reveal:nth-child(2){animation-delay:.07s}.reveal:nth-child(3){animation-delay:.14s}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
@media(max-width:1100px){.cards{grid-template-columns:1fr 1fr}.grid{grid-template-columns:1fr}}
@media(max-width:780px){
  .side{position:static;width:auto;flex-direction:row;align-items:center;padding:14px 16px;border-right:0;border-bottom:1px solid var(--line)}
  .brand{margin:0 18px 0 0}.brand-text small,.nav-label,.side-foot{display:none}
  nav{display:flex;gap:4px;overflow:auto}nav a{padding:9px 11px;font-size:11px}nav a span{display:none}
  .main{margin:0;padding:20px 16px}.topbar{align-items:flex-start;flex-direction:column}
  .cards,.two,.checks{grid-template-columns:1fr}.live{display:none}
}
</style>'''

# Refined ultra-light line icons (stroke-width 1.5, currentColor) — no icon fonts.
I_DASH='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>'
I_ACT='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12h4l3-8 4 16 3-8h4"/></svg>'
I_SIM='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/></svg>'
I_INC='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z"/><path d="M9.5 12.2l1.8 1.8 3.4-3.6"/></svg>'
I_EVAL='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>'
I_LOGO='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"><path d="M12 2l9 4v6c0 6-4 9.5-9 11-5-1.5-9-5-9-11V6l9-4z"/><path d="M8.5 12.2l2.3 2.3 4.7-5"/></svg>'
I_ARROW='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17L17 7M9 7h8v8"/></svg>'
I_WRN='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l9.5 17H2.5L12 3z"/><path d="M12 9v5M12 17.5v.5"/></svg>'
I_LST='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01"/></svg>'

BASE='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>{{title}} · RoadSecure</title>'''+CSS+'''</head><body>
<div class="bg-field"></div><div class="bg-grid"></div>
<aside class="side">
  <a class="brand" href="/"><span class="brand-mark">''' + I_LOGO + '''</span><span class="brand-text">RoadSecure<small>TRANSPORT CYBER DEFENCE</small></span></a>
  <div class="nav-label">OPERATIONS</div>
  <nav>
    <a href="/" data-path="/">''' + I_DASH + '''<span>Dashboard</span></a>
    <a href="/events" data-path="/events">''' + I_ACT + '''<span>Activity &amp; Alerts</span></a>
    <a href="/simulate" data-path="/simulate">''' + I_SIM + '''<span>Simulate Activity</span></a>
    <a href="/incidents" data-path="/incidents">''' + I_INC + '''<span>Incident Management</span></a>
    <a href="/evaluation" data-path="/evaluation">''' + I_EVAL + '''<span>Evaluation</span></a>
  </nav>
  <div class="side-foot"><div class="side-status"><span class="dot"></span>Detector online</div><div class="side-meta">ISOLATION FOREST · 180 TREES</div></div>
</aside>
<main class="main">
  <header class="topbar"><div class="crumb"><small>ROAD TRANSPORT INFORMATION SYSTEMS</small><h1>{{title}}</h1></div>
    <div class="topbar-right"><span class="live"><span class="dot"></span>LIVE MONITORING</span><span class="clock" id="clock">--:--:--</span></div></header>
  {% for m in get_flashed_messages() %}<div class="flash">{{m}}</div>{% endfor %}
  {{body|safe}}
  <div class="footer">RoadSecure · Academic prototype · Synthetic demonstration data only · Keep local, do not expose publicly</div>
</main>
<script>
(function(){
  var p=location.pathname,best=null,bl=0;
  document.querySelectorAll('nav a[data-path]').forEach(function(a){
    var d=a.getAttribute('data-path');if(p===d||(d!=='/'&&p.indexOf(d)===0)&&d.length>bl){best=a;bl=d.length}
  });
  if(best)best.classList.add('active');
  function tick(){var d=new Date();document.getElementById('clock').textContent=[d.getHours(),d.getMinutes(),d.getSeconds()].map(function(n){return String(n).padStart(2,'0')}).join(':')}
  tick();setInterval(tick,1000);
})();
</script></body></html>'''
def page(title,body,**ctx): return render_template_string(BASE,title=title,body=render_template_string(body,**ctx))

@app.get('/')
def dashboard():
 with conn() as c:
  t=c.execute("SELECT COUNT(*) total,SUM(anomaly) alerts,SUM(CASE WHEN anomaly=1 AND severity IN ('High','Critical') THEN 1 ELSE 0 END) high,SUM(CASE WHEN anomaly=1 AND status='Open' THEN 1 ELSE 0 END) opened FROM events").fetchone(); rows=c.execute('SELECT * FROM events ORDER BY id DESC LIMIT 12').fetchall()
 body='''<div class="cards reveal">
  <div class="card tone-cyan"><div class="inner card-body"><div class="stat-top"><span class="stat-label">Monitored events</span><span class="stat-ico">''' + I_LST + '''</span></div><strong class="stat-val">{{t.total or 0}}</strong><div class="stat-foot"><span class="stat-trend"><b>↑ 100%</b> baseline captured</span><svg class="spark" viewBox="0 0 78 26"><polyline points="0,22 10,18 20,20 30,12 40,15 50,9 60,11 70,5 78,7" fill="none" stroke="currentColor" stroke-width="1.5" opacity=".9"/></svg></div></div></div>
  <div class="card tone-violet"><div class="inner card-body"><div class="stat-top"><span class="stat-label">Anomalies detected</span><span class="stat-ico">''' + I_ACT + '''</span></div><strong class="stat-val">{{t.alerts or 0}}</strong><div class="stat-foot"><span class="stat-trend"><b>◆</b> unsupervised ML</span><svg class="spark" viewBox="0 0 78 26"><polyline points="0,20 12,20 22,14 32,17 44,8 54,12 66,6 78,9" fill="none" stroke="currentColor" stroke-width="1.5" opacity=".9"/></svg></div></div></div>
  <div class="card tone-amber"><div class="inner card-body"><div class="stat-top"><span class="stat-label">High / critical</span><span class="stat-ico">''' + I_WRN + '''</span></div><strong class="stat-val">{{t.high or 0}}</strong><div class="stat-foot"><span class="stat-trend"><b>!</b> priority review</span><svg class="spark" viewBox="0 0 78 26"><polyline points="0,22 10,19 20,21 30,14 40,18 50,10 60,14 70,6 78,10" fill="none" stroke="currentColor" stroke-width="1.5" opacity=".9"/></svg></div></div></div>
  <div class="card tone-green"><div class="inner card-body"><div class="stat-top"><span class="stat-label">Open alerts</span><span class="stat-ico">''' + I_INC + '''</span></div><strong class="stat-val">{{t.opened or 0}}</strong><div class="stat-foot"><span class="stat-trend"><b>●</b> awaiting triage</span><svg class="spark" viewBox="0 0 78 26"><polyline points="0,18 10,20 20,14 30,16 40,11 50,13 60,8 70,10 78,5" fill="none" stroke="currentColor" stroke-width="1.5" opacity=".9"/></svg></div></div></div>
 </div>
 <div class="panel reveal"><div class="inner"><div class="panel-head"><h2>''' + I_ACT + '''Recent monitored activity</h2><span class="muted">Latest {{rows|length}} records</span></div>
  <div class="panel-body"><div class="tablewrap"><table><thead><tr><th>Event / Time</th><th>Identity</th><th>Activity</th><th>Risk</th><th>Status</th></tr></thead><tbody>{% for r in rows %}<tr><td class="id">#{{r.id}}<span class="stack"><small>{{r.timestamp[11:19]}}</small></span></td><td><strong>{{r['user']}}</strong><span class="stack"><small>{{r.device}}</small></span></td><td>{{r.event_type}}</td><td><span class="pill {{r.severity|lower}}">{{r.severity}}</span></td><td><span class="status-pill">{{r.status}}</span></td></tr>{% endfor %}</tbody></table></div>
  <div class="btn-row"><a class="btn" href="/simulate">Simulate activity <span class="ico">''' + I_ARROW + '''</span></a><a class="btn secondary" href="/incidents">Manage incidents</a><form method=post action="/reset" onsubmit="return confirm('Reset all demo data?')"><button class="ghost" type="submit">Reset demo data</button></form></div></div></div></div>'''
 return page('Security overview',body,t=t,rows=rows)
@app.get('/events')
def events():
 status=request.args.get('status','All')
 with conn() as c:
  if status=='Alerts': rows=c.execute('SELECT * FROM events WHERE anomaly=1 ORDER BY id DESC').fetchall()
  elif status in ('Open','Investigating','Resolved'): rows=c.execute('SELECT * FROM events WHERE status=? ORDER BY id DESC',(status,)).fetchall()
  else: rows=c.execute('SELECT * FROM events ORDER BY id DESC').fetchall()
 body='''<div class="panel reveal"><div class="inner"><div class="panel-head"><h2>''' + I_ACT + '''Event register</h2><div class="filters">{% for s in ['All','Alerts','Open','Investigating','Resolved'] %}<a href="/events?status={{s}}" class="{% if s==status %}on{% endif %}">{{s}}</a>{% endfor %}</div></div>
  <div class="panel-body"><div class="tablewrap"><table><thead><tr><th>Event / Time</th><th>Identity</th><th>Source IP</th><th>Signals</th><th>Score</th><th>Risk</th><th>Status</th><th>Update</th></tr></thead><tbody>{% for r in rows %}<tr><td class="id">#{{r.id}}<span class="stack"><small>{{r.timestamp[11:19]}}</small></span></td><td><strong>{{r['user']}}</strong><span class="stack"><small>{{r.device}}</small></span></td><td class="mono">{{r.ip}}</td><td><span class="stack">Fails {{r.login_failures}} · {{r.requests_per_minute|round|int}} req/min<small>{{r.bytes_sent_mb|round(1)}} MB sent · scans {{r.port_scan_events}}</small></span></td><td class="mono"><strong>{{r.score}}</strong></td><td><span class="pill {{r.severity|lower}}">{{r.severity}}</span></td><td><span class="status-pill">{{r.status}}</span></td><td><form method=post action="/event/{{r.id}}" style="display:flex;gap:6px"><select name=status style="width:auto;padding:7px 8px"><option>Open</option><option>Investigating</option><option>Resolved</option><option>Normal</option></select><button class="ghost" style="border-radius:9px" type="submit">Save</button></form></td></tr>{% endfor %}</tbody></table></div></div></div></div>'''
 return page('Activity & alerts',body,rows=rows,status=status)
@app.post('/event/<int:eid>')
def event_status(eid):
 with conn() as c:c.execute('UPDATE events SET status=? WHERE id=?',(request.form['status'],eid))
 flash('Event status updated.');return redirect('/events')
@app.route('/simulate',methods=['GET','POST'])
def simulate():
 result=None
 if request.method=='POST':
  r={'user':request.form.get('user','user'),'device':request.form.get('device','device'),'ip':request.form.get('ip','10.0.0.1'),'event_type':request.form.get('event_type','Login'),'login_failures':int(request.form.get('login_failures',0)),'requests_per_minute':float(request.form.get('requests_per_minute',30)),'bytes_sent_mb':float(request.form.get('bytes_sent_mb',2)),'outside_hours':int('outside_hours' in request.form),'new_device':int('new_device' in request.form),'unusual_location':int('unusual_location' in request.form),'privilege_change':int('privilege_change' in request.form),'port_scan_events':int(request.form.get('port_scan_events',0))}
  result=save_event(r);flash('Activity analysed and stored.')
 body='''<div class="grid"><section class="panel reveal"><div class="inner"><div class="panel-head"><h2>''' + I_SIM + '''Submit activity record</h2></div><div class="panel-body"><p class="muted" style="margin-top:0">Synthetic user, device and network telemetry. The detector analyses and stores each record.</p>
  <form class="form" method=post><div class="two"><label>Username<input name=user value=operator01 required></label><label>Device ID<input name=device value=TERM-001 required></label><label>Source IP<input name=ip value=10.0.1.24></label><label>Event type<select name=event_type><option>Login</option><option>Record access</option><option>Payment query</option><option>Device activity</option><option>Network activity</option></select></label><label>Failed logins<input type=number name=login_failures value=0 min=0></label><label>Requests / minute<input type=number step=.1 name=requests_per_minute value=35 min=0></label><label>Data sent (MB)<input type=number step=.1 name=bytes_sent_mb value=2 min=0></label><label>Port scan events<input type=number name=port_scan_events value=0 min=0></label></div>
  <div class="section-cap">Additional indicators</div><div class="checks"><label><input type=checkbox name=outside_hours> Outside normal hours</label><label><input type=checkbox name=new_device> New device</label><label><input type=checkbox name=unusual_location> Unusual location</label><label><input type=checkbox name=privilege_change> Privilege change</label></div>
  <button type=submit>Analyse activity <span class="ico">''' + I_ARROW + '''</span></button></form></div></div></section>
 <section class="panel reveal"><div class="inner"><div class="panel-head"><h2>''' + I_ACT + '''Detection result</h2></div><div class="panel-body">
  {% if result %}<div class="result"><div class="gauge {{result[3]|lower}}" style="--score:{{result[2]}}"><div class="gauge-inner"><strong>{{result[2]}}</strong><small>RISK SCORE / 100</small></div></div>
   <div class="result-lines"><div class="result-line"><span>Anomaly detected</span><b>{{'Yes' if result[1] else 'No'}}</b></div><div class="result-line"><span>Severity</span><b><span class="pill {{result[3]|lower}}">{{result[3]}}</span></b></div><div class="result-line"><span>Event reference</span><b>#{{result[0]}}</b></div></div></div>
  {% else %}<div class="result"><div class="gauge" style="--score:0"><div class="gauge-inner"><strong>—</strong><small>AWAITING INPUT</small></div></div><p class="muted" style="max-width:280px;text-align:center">Submit a record to see the anomaly score and severity here.</p></div>{% endif %}
  <div class="section-cap" style="margin-top:20px">Try suspicious activity</div><p class="tip">Use <code>8</code> failed logins, <code>220</code> req/min, <code>75</code> MB, <code>6</code> port scans — and select all four indicators.</p>
 </div></div></section></div>'''
 return page('Simulate monitored activity',body,result=result)
@app.route('/incidents',methods=['GET','POST'])
def incidents():
 if request.method=='POST':
  with conn() as c:
   c.execute('INSERT INTO incidents(event_id,title,priority,assignee,status,notes,created) VALUES(?,?,?,?,?,?,?)',(request.form['event_id'],request.form['title'],request.form['priority'],request.form.get('assignee',''),'Open',request.form.get('notes',''),datetime.now().isoformat(timespec='seconds')))
   c.execute("UPDATE events SET status='Investigating' WHERE id=?",(request.form['event_id'],))
  flash('Incident created.');return redirect('/incidents')
 with conn() as c:
  alerts=c.execute('SELECT id,"user",device,severity FROM events WHERE anomaly=1 ORDER BY id DESC').fetchall(); rows=c.execute('SELECT i.*,e."user",e.device FROM incidents i LEFT JOIN events e ON e.id=i.event_id ORDER BY i.id DESC').fetchall()
 body='''<div class="grid"><section class="panel reveal"><div class="inner"><div class="panel-head"><h2>''' + I_INC + '''Create incident record</h2></div><div class="panel-body"><form method=post class="form"><label>Related anomaly<select name=event_id required>{% for a in alerts %}<option value={{a.id}}>#{{a.id}} — {{a['user']}} / {{a.device}} ({{a.severity}})</option>{% endfor %}</select></label><label>Incident title<input name=title required placeholder="Unusual terminal activity"></label><div class="two"><label>Priority<select name=priority><option>Critical</option><option>High</option><option selected>Medium</option><option>Low</option></select></label><label>Assigned to<input name=assignee placeholder="Security analyst"></label></div><label>Investigation notes<textarea name=notes rows=4></textarea></label><button {% if not alerts %}disabled{% endif %}>Create incident <span class="ico">''' + I_ARROW + '''</span></button></form>{% if not alerts %}<p class="muted" style="margin-top:14px">Simulate an anomaly first.</p>{% endif %}</div></div></section>
 <section class="panel reveal"><div class="inner"><div class="panel-head"><h2>''' + I_LST + '''Incident register</h2><span class="muted">{{rows|length}} records</span></div><div class="panel-body"><div class="tablewrap"><table><thead><tr><th>ID</th><th>Event</th><th>Title</th><th>Priority</th><th>Status</th></tr></thead><tbody>{% for r in rows %}<tr><td class="id">#{{r.id}}</td><td class="mono">#{{r.event_id}} {{r['user']}}/{{r.device}}</td><td><strong>{{r.title}}</strong></td><td><span class="pill {{r.priority|lower}}">{{r.priority}}</span></td><td><span class="status-pill">{{r.status}}</span></td></tr>{% else %}<tr><td colspan=5 class="muted">No incidents recorded yet.</td></tr>{% endfor %}</tbody></table></div></div></div></section></div>'''
 return page('Incident management',body,alerts=alerts,rows=rows)
@app.get('/evaluation')
def evaluation():
 with conn() as c:
  total=c.execute('SELECT COUNT(*) FROM events').fetchone()[0]; alerts=c.execute('SELECT COUNT(*) FROM events WHERE anomaly=1').fetchone()[0]
 body='''<div class="cards reveal"><div class="card tone-cyan"><div class="inner card-body"><div class="stat-top"><span class="stat-label">Events processed</span></div><strong class="stat-val">{{total}}</strong><div class="stat-foot"><span class="stat-trend">Stored records</span></div></div></div><div class="card tone-violet"><div class="inner card-body"><div class="stat-top"><span class="stat-label">Predicted anomalies</span></div><strong class="stat-val">{{alerts}}</strong><div class="stat-foot"><span class="stat-trend">Flagged by detector</span></div></div></div><div class="card tone-green"><div class="inner card-body"><div class="stat-top"><span class="stat-label">Predicted normal</span></div><strong class="stat-val">{{total-alerts}}</strong><div class="stat-foot"><span class="stat-trend">Baseline behaviour</span></div></div></div></div>
 <div class="notice reveal">''' + I_WRN + '''<div><b>Evaluation scope — prototype counts only</b><span>Accuracy, precision, recall, false-positive rate and response time are not claimed: independently labelled ground truth and controlled timing measurements are not yet available.</span></div></div>
 <div class="panel reveal"><div class="inner"><div class="panel-head"><h2>''' + I_EVAL + '''Evaluation plan &amp; metric definitions</h2><span class="muted">Definitions</span></div><div class="panel-body"><div class="formulas">
  <div class="formula"><span class="n">01</span><div><code>Accuracy = (TP + TN) / (TP + TN + FP + FN)</code><p>Overall correctness once labelled data exists.</p></div></div>
  <div class="formula"><span class="n">02</span><div><code>Precision = TP / (TP + FP)</code><p>How many alerts were genuinely anomalous.</p></div></div>
  <div class="formula"><span class="n">03</span><div><code>Recall = TP / (TP + FN)</code><p>How many real anomalies were caught.</p></div></div>
  <div class="formula"><span class="n">04</span><div><code>False-positive rate = FP / (FP + TN)</code><p>Normal events incorrectly flagged.</p></div></div>
  <div class="formula"><span class="n">05</span><div><code>Response time = alert display − event submission</code><p>Measured under controlled timing conditions.</p></div></div>
 </div><p class="muted" style="margin:16px 0 0">The Isolation Forest detector is trained on synthetic normal baseline data. Scores are demonstration outputs, not validated real-world performance.</p></div></div></div>'''
 return page('Prototype evaluation',body,total=total,alerts=alerts)
@app.get('/api/summary')
def api():
 with conn() as c:r=c.execute('SELECT COUNT(*) total,SUM(anomaly) anomalies,SUM(CASE WHEN anomaly=1 AND status="Open" THEN 1 ELSE 0 END) open_alerts FROM events').fetchone()
 return jsonify(dict(r))
@app.post('/reset')
def reset():
 with conn() as c:c.execute('DELETE FROM incidents');c.execute('DELETE FROM events')
 init_seed();flash('Demo data reset.');return redirect('/')
def init_seed():
 random.seed(7)
 for i in range(70):
  bad=i%11==0;r={'user':random.choice(['operator01','inspector02','payments03','admin01']),'device':random.choice(['TERM-01','GATE-04','PAY-08','SRV-CORE']),'ip':f'10.0.{random.randint(1,5)}.{random.randint(2,250)}','event_type':'Login','login_failures':random.randint(4,10) if bad else random.choice([0,0,1]),'requests_per_minute':random.uniform(160,280) if bad else random.uniform(10,65),'bytes_sent_mb':random.uniform(40,100) if bad else random.uniform(.1,8),'outside_hours':int(bad),'new_device':int(bad),'unusual_location':int(bad),'privilege_change':int(bad and random.random()>.6),'port_scan_events':random.randint(3,10) if bad else 0};save_event(r)
init();
if __name__=='__main__': app.run(host='127.0.0.1',port=5000,debug=False)
