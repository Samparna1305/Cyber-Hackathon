#!/usr/bin/env python3
"""
================================================================
  dashboard.py — Real-time MitM Traffic Dashboard
  Hackathon #31: TLS Certificate Pinning Bypass & MitM Attack
================================================================

Serves a live web dashboard at http://localhost:5001 that shows
intercepted traffic in real time as mitmproxy captures it.

USAGE:
  python3 dashboard.py
  # Open http://localhost:5001 in browser
================================================================
"""

import json
import os
import sys
from pathlib import Path
from flask import Flask, jsonify, render_template_string

LOG_FILE = os.path.join(os.path.dirname(__file__), "..", "mitm", "intercepted_traffic.json")

app = Flask(__name__)

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MitM Live Dashboard — Hackathon #31</title>
<style>
  :root {
    --bg:#0d1117; --bg2:#161b22; --bg3:#21262d;
    --red:#f85149; --green:#3fb950; --yellow:#d29922;
    --blue:#79c0ff; --text:#c9d1d9; --border:#30363d;
  }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:var(--text);
         font:13px/1.5 'Courier New',monospace; }
  #header { background:var(--red); padding:16px 24px; display:flex;
            align-items:center; justify-content:space-between; }
  #header h1 { color:#fff; font-size:18px; }
  #status-dot { width:10px; height:10px; background:#0f0; border-radius:50%;
                display:inline-block; margin-right:6px;
                animation:blink 1s infinite; }
  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }
  #stats { display:grid; grid-template-columns:repeat(4,1fr);
           gap:12px; padding:16px 24px; background:var(--bg2);
           border-bottom:1px solid var(--border); }
  .stat { text-align:center; }
  .stat .n { font-size:28px; font-weight:700; }
  .stat .l { font-size:10px; color:#888; text-transform:uppercase; margin-top:2px; }
  .n.red { color:var(--red); } .n.grn { color:var(--green); }
  .n.yel { color:var(--yellow); } .n.blu { color:var(--blue); }
  #feed { padding:16px 24px; height:calc(100vh - 200px); overflow-y:auto; }
  .entry { background:var(--bg2); border:1px solid var(--border);
           border-radius:6px; margin-bottom:10px; overflow:hidden;
           animation:fadeIn .3s ease; }
  @keyframes fadeIn { from{opacity:0;transform:translateY(-4px)} to{opacity:1} }
  .entry-header { display:flex; align-items:center; gap:10px;
                  padding:10px 14px; background:var(--bg3); cursor:pointer; }
  .entry-header:hover { background:#2d333b; }
  .badge { padding:2px 8px; border-radius:4px; font-size:11px; font-weight:700; }
  .req { background:#1f6feb; color:#fff; }
  .resp { background:#1a4731; color:var(--green); }
  .err { background:#3d1a1a; color:var(--red); }
  .url { color:var(--blue); flex:1; overflow:hidden; text-overflow:ellipsis;
         white-space:nowrap; font-size:12px; }
  .ts { color:#888; font-size:11px; white-space:nowrap; }
  .entry-body { padding:12px 14px; font-size:12px; color:#aaa;
                border-top:1px solid var(--border); display:none; }
  .entry-body.open { display:block; }
  .entry-body pre { white-space:pre-wrap; word-break:break-all; }
  .cert-info { background:var(--bg3); border-radius:4px; padding:8px 10px;
               margin-top:8px; font-size:11px; color:var(--yellow); }
  #empty { text-align:center; color:#888; padding:60px; font-size:16px; }
</style>
</head>
<body>
<div id="header">
  <h1>⚔ MitM Live Traffic Dashboard</h1>
  <div><span id="status-dot"></span><span id="status-text" style="color:#fff">Listening on port 8080...</span></div>
</div>
<div id="stats">
  <div class="stat"><div class="n red" id="s-total">0</div><div class="l">Total Entries</div></div>
  <div class="stat"><div class="n blu" id="s-req">0</div><div class="l">Requests</div></div>
  <div class="stat"><div class="n grn" id="s-resp">0</div><div class="l">Responses</div></div>
  <div class="stat"><div class="n yel" id="s-creds">0</div><div class="l">Credentials Found</div></div>
</div>
<div id="feed"><div id="empty">⏳ Waiting for intercepted traffic...<br><small>Make sure mitmproxy and Frida are running.</small></div></div>

<script>
let seen = 0;

function toggle(el) {
  el.classList.toggle('open');
}

function renderEntry(e, i) {
  const isReq   = e.direction === 'REQUEST';
  const code    = e.status_code || '';
  const badge   = isReq ? '<span class="badge req">REQ</span>'
                        : `<span class="badge ${String(code).startsWith('2') ? 'resp' : 'err'}">${code}</span>`;
  const url     = (e.url || '').replace(/https?:\/\//, '');
  const method  = isReq ? `<strong>${e.method}</strong> ` : '';

  let body = '';
  if (e.body) {
    try { body = JSON.stringify(JSON.parse(e.body), null, 2); }
    catch { body = e.body; }
  }

  let certHtml = '';
  if (e.cert_info && e.cert_info.subject) {
    certHtml = `<div class="cert-info">🔒 Server cert CN: ${e.cert_info.subject} | Expires: ${e.cert_info.not_after || 'N/A'}</div>`;
  }

  return `
    <div class="entry">
      <div class="entry-header" onclick="this.nextElementSibling.classList.toggle('open')">
        ${badge}
        <span class="url">${method}${url}</span>
        <span class="ts">${(e.timestamp||'').replace('T',' ').replace('Z','')}</span>
      </div>
      <div class="entry-body">
        ${body ? `<pre>${body.replace(/</g,'&lt;').replace(/>/g,'&gt;').substring(0, 2000)}</pre>` : '<em>No body</em>'}
        ${certHtml}
      </div>
    </div>`;
}

async function poll() {
  try {
    const r = await fetch('/api/traffic');
    const data = await r.json();
    const entries = data.entries || [];

    document.getElementById('s-total').textContent = entries.length;
    document.getElementById('s-req').textContent   = entries.filter(e=>e.direction==='REQUEST').length;
    document.getElementById('s-resp').textContent  = entries.filter(e=>e.direction==='RESPONSE').length;
    document.getElementById('s-creds').textContent = entries.filter(e=>(e.body||'').includes('token')).length;

    if (entries.length > seen) {
      const feed = document.getElementById('feed');
      const empty = document.getElementById('empty');
      if (empty) empty.remove();

      for (let i = seen; i < entries.length; i++) {
        feed.insertAdjacentHTML('afterbegin', renderEntry(entries[i], i));
      }
      seen = entries.length;
    }
  } catch(e) { /* log not available yet */ }
}

setInterval(poll, 1000);
poll();
</script>
</body>
</html>"""


@app.route("/")
def index():
    return DASHBOARD_HTML


@app.route("/api/traffic")
def traffic():
    entries = []
    log_path = Path(LOG_FILE)
    if log_path.exists():
        try:
            with open(log_path) as f:
                entries = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return jsonify({"entries": entries, "count": len(entries)})


@app.route("/api/clear", methods=["POST"])
def clear():
    log_path = Path(LOG_FILE)
    if log_path.exists():
        log_path.write_text("[]")
    return jsonify({"status": "cleared"})


if __name__ == "__main__":
    print(f"\n  🌐 MitM Dashboard → http://localhost:5001")
    print(f"  📡 Reading traffic from: {LOG_FILE}")
    print(f"  Press Ctrl+C to stop\n")
    app.run(host="0.0.0.0", port=5001, debug=False)
