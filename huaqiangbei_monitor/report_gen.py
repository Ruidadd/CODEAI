"""生成全量静态 HTML 报告 — 所有数据内嵌为 JSON, 不依赖后端服务器

Chart.js 从 CDN 加载(浏览器需能访问 cdn.jsdelivr.net),
其余无任何外部依赖, 生成的 .html 文件可直接在浏览器中打开。
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .storage import PriceStorage


_CHART_JS = "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def collect_data(storage: PriceStorage, history_days: int = 7) -> dict:
    components = storage.list_components(active_only=True)
    stats = storage.get_stats()
    alerts = storage.get_recent_alerts(hours=72)

    comp_rows = []
    charts = {}

    for comp in components:
        latest = storage.get_latest_prices(comp.part_number)

        prices = []
        for r in latest:
            two = storage.get_latest_two(comp.part_number, r.source)
            change_pct = None
            if len(two) == 2 and two[1].price > 0:
                change_pct = round((two[0].price - two[1].price) / two[1].price * 100, 2)
            prices.append({
                "source": r.source,
                "source_name": r.source_name,
                "price": r.price,
                "min_qty": r.min_qty,
                "stock_qty": r.stock_qty,
                "supplier": r.supplier,
                "url": r.url,
                "change_pct": change_pct,
                "scraped_at": _iso(r.scraped_at),
            })

        best = latest[0] if latest else None
        change_pct = None
        if best:
            two = storage.get_latest_two(comp.part_number, best.source)
            if len(two) == 2 and two[1].price > 0:
                change_pct = round((two[0].price - two[1].price) / two[1].price * 100, 2)

        comp_rows.append({
            "part_number": comp.part_number,
            "description": comp.description or "",
            "category": comp.category or "",
            "best_price": best.price if best else None,
            "best_source": best.source_name if best else None,
            "change_pct": change_pct,
            "prices": prices,
        })

        history = storage.get_price_history(comp.part_number, days=history_days)
        series: dict[str, dict] = {}
        for r in history:
            s = series.setdefault(r.source, {
                "source_name": r.source_name,
                "points": [],
            })
            s["points"].append({"t": _iso(r.scraped_at), "price": r.price})
        charts[comp.part_number] = list(series.values())

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "stats": stats,
        "components": comp_rows,
        "charts": charts,
        "alerts": [
            {
                "part_number": a.part_number,
                "source": a.source,
                "old_price": a.old_price,
                "new_price": a.new_price,
                "change_pct": round(a.change_pct, 2),
                "direction": a.direction,
                "alerted_at": _iso(a.alerted_at),
            }
            for a in alerts
        ],
    }


def render_html(data: dict) -> str:
    data_json = json.dumps(data, ensure_ascii=False)
    gen_time = data["generated_at"].replace("T", " ")[:16] + " UTC"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>华强北价格监控 — {gen_time}</title>
<script src="{_CHART_JS}"></script>
<style>
  :root {{
    --bg:#0d1117;--panel:#161b22;--border:#30363d;
    --text:#e6edf3;--muted:#8b949e;
    --up:#f85149;--down:#3fb950;--accent:#58a6ff;
  }}
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{background:var(--bg);color:var(--text);
    font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;min-height:100vh}}
  header{{padding:14px 24px;border-bottom:1px solid var(--border);
    background:var(--panel);display:flex;align-items:center;flex-wrap:wrap;gap:16px}}
  header h1{{font-size:18px}}
  .spacer{{flex:1}}
  .stat{{font-size:13px;color:var(--muted)}} .stat b{{color:var(--text)}}
  .badge{{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11px;
    background:#21262d;border:1px solid var(--border)}}
  main{{display:grid;grid-template-columns:360px 1fr;gap:16px;
    padding:16px 24px;max-width:1500px;margin:0 auto}}
  @media(max-width:900px){{main{{grid-template-columns:1fr}}}}
  .panel{{background:var(--panel);border:1px solid var(--border);border-radius:8px;overflow:hidden}}
  .panel h2{{font-size:13px;color:var(--muted);font-weight:600;
    padding:10px 14px;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:8px}}
  table{{width:100%;border-collapse:collapse;font-size:13px}}
  th,td{{padding:8px 14px;text-align:left;white-space:nowrap}}
  th{{color:var(--muted);font-weight:500;font-size:12px}}
  tbody tr{{border-top:1px solid var(--border)}}
  tbody tr:hover{{background:#1c2128}}
  .num{{text-align:right;font-variant-numeric:tabular-nums}}
  #partList tbody tr{{cursor:pointer}}
  #partList tbody tr.active{{background:#1f2937;box-shadow:inset 3px 0 0 var(--accent)}}
  .price{{font-weight:600}}
  .up{{color:var(--up)}} .down{{color:var(--down)}} .muted{{color:var(--muted)}}
  .chart-wrap{{padding:14px;height:320px}}
  .right-col{{display:flex;flex-direction:column;gap:16px}}
  #alertFeed{{max-height:260px;overflow-y:auto}}
  .alert-item{{display:flex;gap:10px;align-items:baseline;
    padding:8px 14px;border-top:1px solid var(--border);font-size:13px}}
  .alert-item .t{{color:var(--muted);font-size:11px;margin-left:auto}}
  .empty{{padding:24px;text-align:center;color:var(--muted);font-size:13px}}
  .gen-note{{font-size:11px;color:var(--muted);padding:8px 14px;
    border-top:1px solid var(--border);text-align:right}}
</style>
</head>
<body>
<header>
  <h1>📊 华强北元器件价格监控</h1>
  <span class="stat">型号 <b id="stTotal">-</b></span>
  <span class="stat">价格记录 <b id="stRecords">-</b></span>
  <span class="stat">告警 <b id="stAlerts">-</b></span>
  <div class="spacer"></div>
  <span class="stat">快照时间 <b>{gen_time}</b></span>
</header>
<main>
  <div class="panel">
    <h2>监控型号 <span class="badge" id="partCount">0</span></h2>
    <table id="partList">
      <thead><tr><th>型号</th><th class="num">最低价(¥)</th><th class="num">环比</th><th>来源</th></tr></thead>
      <tbody></tbody>
    </table>
    <div class="empty" id="partEmpty" style="display:none">暂无数据</div>
  </div>
  <div class="right-col">
    <div class="panel">
      <h2>各来源最新报价 — <span id="detailTitle" style="color:var(--accent)">点击左侧型号</span></h2>
      <table id="priceTable">
        <thead><tr>
          <th>来源</th><th class="num">单价(¥)</th><th class="num">环比</th>
          <th class="num">起购</th><th class="num">库存</th><th>供应商</th><th>更新</th>
        </tr></thead>
        <tbody></tbody>
      </table>
      <div class="empty" id="priceEmpty">点击左侧型号查看报价详情</div>
    </div>
    <div class="panel">
      <h2>价格走势
        <select id="daysSel" onchange="changeRange()" style="background:#21262d;color:var(--text);border:1px solid var(--border);border-radius:6px;padding:2px 6px">
          <option value="1">24小时</option>
          <option value="7" selected>7天</option>
          <option value="all">全部</option>
        </select>
      </h2>
      <div class="chart-wrap"><canvas id="chart"></canvas></div>
    </div>
    <div class="panel">
      <h2>价格变化告警(72h)</h2>
      <div id="alertFeed"></div>
    </div>
  </div>
</main>
<div style="text-align:center;color:var(--muted);font-size:12px;padding:12px">
  静态快照 · 数据截至 {gen_time} · 实时监控请在本地运行 <code style="background:#21262d;padding:2px 6px;border-radius:4px">python main.py web</code>
</div>

<script>
const DATA = {data_json};
let currentPart = null, chart = null;
const COLORS = ['#58a6ff','#f0883e','#3fb950','#d2a8ff','#f85149','#79c0ff'];

const fmtP  = p => p == null ? '-' : Number(p).toFixed(4);
const fmtT  = iso => iso ? iso.replace('T',' ').slice(5,16) : '-';
const fmtPct = pct => {{
  if(pct==null) return '<span class="muted">-</span>';
  const cls = pct>0?'up':(pct<0?'down':'muted');
  const arrow = pct>0?'▲':(pct<0?'▼':'');
  return `<span class="${{cls}}">${{arrow}} ${{Math.abs(pct).toFixed(2)}}%</span>`;
}};

function boot() {{
  const s = DATA.stats;
  document.getElementById('stTotal').textContent   = s.total_components;
  document.getElementById('stRecords').textContent = s.total_records;
  document.getElementById('stAlerts').textContent  = s.total_alerts;

  const parts = DATA.components;
  document.getElementById('partCount').textContent = parts.length;
  document.getElementById('partEmpty').style.display = parts.length ? 'none' : '';

  const tbody = document.querySelector('#partList tbody');
  tbody.innerHTML = parts.map(p => `
    <tr data-part="${{p.part_number}}"
        class="${{p.part_number===currentPart?'active':''}}"
        onclick="selectPart('${{p.part_number}}')">
      <td><b>${{p.part_number}}</b></td>
      <td class="num price">${{fmtP(p.best_price)}}</td>
      <td class="num">${{fmtPct(p.change_pct)}}</td>
      <td class="muted">${{p.best_source??'-'}}</td>
    </tr>`).join('');

  renderAlerts();
  if(parts.length) selectPart(parts[0].part_number);
}}

function selectPart(part) {{
  currentPart = part;
  document.querySelectorAll('#partList tbody tr').forEach(tr =>
    tr.classList.toggle('active', tr.dataset.part===part));
  const comp = DATA.components.find(c=>c.part_number===part);
  if(!comp) return;

  document.getElementById('detailTitle').textContent = part;
  const tbody = document.querySelector('#priceTable tbody');
  const rows = comp.prices;
  document.getElementById('priceEmpty').style.display = rows.length ? 'none' : '';
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td>${{r.url?`<a href="${{r.url}}" target="_blank" style="color:var(--accent)">${{r.source_name}}</a>`:r.source_name}}</td>
      <td class="num price">${{fmtP(r.price)}}</td>
      <td class="num">${{fmtPct(r.change_pct)}}</td>
      <td class="num">${{r.min_qty??'-'}}</td>
      <td class="num">${{r.stock_qty??'-'}}</td>
      <td class="muted">${{r.supplier??'-'}}</td>
      <td class="muted">${{fmtT(r.scraped_at)}}</td>
    </tr>`).join('');

  drawChart(part);
}}

function changeRange() {{ if(currentPart) drawChart(currentPart); }}

function drawChart(part) {{
  const days = document.getElementById('daysSel').value;
  let allSeries = DATA.charts[part] || [];
  const cutoff = days==='all' ? null : Date.now() - Number(days)*86400000;
  const datasets = allSeries.map((s,i) => ({{
    label: s.source_name,
    data: s.points
      .filter(p => !cutoff || new Date(p.t+'Z').getTime()>=cutoff)
      .map(p => ({{ x: new Date(p.t+'Z').getTime(), y: p.price }})),
    borderColor: COLORS[i%COLORS.length],
    backgroundColor: COLORS[i%COLORS.length],
    tension:.25, pointRadius:3, borderWidth:2,
  }}));
  if(chart) chart.destroy();
  chart = new Chart(document.getElementById('chart'), {{
    type:'line', data:{{ datasets }},
    options:{{
      responsive:true, maintainAspectRatio:false,
      interaction:{{mode:'nearest',intersect:false}},
      plugins:{{
        legend:{{ labels:{{ color:'#e6edf3', boxWidth:12 }} }},
        tooltip:{{ callbacks:{{
          title: items => new Date(items[0].parsed.x).toLocaleString('zh-CN'),
          label: item => ` ${{item.dataset.label}}: ¥${{item.parsed.y.toFixed(4)}}`,
        }} }},
      }},
      scales:{{
        x:{{ type:'linear',
          ticks:{{ color:'#8b949e', maxTicksLimit:8,
            callback: v => {{ const d=new Date(v); return `${{d.getMonth()+1}}-${{d.getDate()}} ${{String(d.getHours()).padStart(2,'0')}}:${{String(d.getMinutes()).padStart(2,'0')}}`; }}
          }},
          grid:{{ color:'#21262d' }},
        }},
        y:{{ ticks:{{ color:'#8b949e', callback: v=>'¥'+v }}, grid:{{ color:'#21262d' }} }},
      }},
    }},
  }});
}}

function renderAlerts() {{
  const feed = document.getElementById('alertFeed');
  const alerts = DATA.alerts;
  feed.innerHTML = alerts.length ? alerts.map(a => `
    <div class="alert-item">
      <b>${{a.part_number}}</b>
      <span class="muted">${{a.source}}</span>
      <span>¥${{fmtP(a.old_price)}} → <b class="${{a.direction==='up'?'up':'down'}}">¥${{fmtP(a.new_price)}}</b></span>
      ${{fmtPct(a.change_pct)}}
      <span class="t">${{fmtT(a.alerted_at)}}</span>
    </div>`).join('')
    : '<div class="empty">最近 72 小时无告警</div>';
}}

boot();
</script>
</body>
</html>"""


def generate_report(
    db_path: Optional[str] = None,
    output_path: Optional[str] = None,
    history_days: int = 7,
) -> str:
    storage = PriceStorage(db_path)
    data = collect_data(storage, history_days)
    html = render_html(data)
    if output_path is None:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M")
        output_path = f"price_report_{ts}.html"
    Path(output_path).write_text(html, encoding="utf-8")
    return output_path
