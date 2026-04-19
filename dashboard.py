"""
ShopWave Web Dashboard
Run: python dashboard.py
Open: http://localhost:5000
"""
import asyncio
import json
import os
import time
import threading
from flask import Flask, render_template_string, jsonify, request

app = Flask(__name__)

# Global state
_job_results = {}
_job_status = {}

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ShopWave - Autonomous Resolution Dashboard</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Fira+Code:wght@400;700&display=swap" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root { 
            --sw-primary: #00f2fe; 
            --sw-secondary: #4facfe;
            --sw-bg: #0b0e14; 
            --sw-card: rgba(22, 27, 34, 0.7); 
            --sw-border: rgba(48, 54, 61, 0.5); 
            --sw-glass: rgba(255, 255, 255, 0.05);
        }
        body { 
            background: radial-gradient(circle at top right, #1a2a44, #0b0e14); 
            color: #e6edf3; 
            font-family: 'Inter', -apple-system, sans-serif;
            min-height: 100vh;
        }
        .navbar { 
            background: rgba(13, 17, 23, 0.8) !important; 
            backdrop-filter: blur(10px);
            border-bottom: 1px solid var(--sw-border); 
            padding: 1rem 2rem;
        }
        .brand-text { 
            background: linear-gradient(to right, var(--sw-primary), var(--sw-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800; 
            font-size: 1.5rem;
            letter-spacing: -1px; 
        }
        .hero { padding: 60px 0 40px; text-align: center; }
        .hero h1 { font-size: 3rem; font-weight: 800; margin-bottom: 1rem; letter-spacing: -1.5px; }
        .hero p { color: #8b949e; font-size: 1.2rem; max-width: 600px; margin: 0 auto; }
        
        .btn-run {
            background: linear-gradient(135deg, var(--sw-primary), var(--sw-secondary));
            border: none; font-weight: 700; padding: 14px 40px; border-radius: 12px;
            color: #000; transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            box-shadow: 0 8px 15px rgba(0, 242, 254, 0.2);
        }
        .btn-run:hover:not(:disabled) { 
            transform: translateY(-3px) scale(1.02); 
            box-shadow: 0 12px 25px rgba(0, 242, 254, 0.4);
            color: #000; 
        }
        .btn-run:disabled { opacity: 0.6; cursor: not-allowed; filter: grayscale(0.5); }

        .metric-card {
            background: var(--sw-card); 
            backdrop-filter: blur(12px);
            border: 1px solid var(--sw-border);
            border-radius: 16px; padding: 25px; 
            text-align: center; transition: all 0.3s ease;
            position: relative; overflow: hidden;
        }
        .metric-card::after {
            content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.03) 0%, transparent 70%);
            pointer-events: none;
        }
        .metric-card:hover { transform: translateY(-5px); border-color: var(--sw-primary); background: rgba(22, 27, 34, 0.9); }
        .metric-value { font-size: 2.8rem; font-weight: 800; margin-bottom: 5px; }
        .metric-label { color: #8b949e; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1.5px; }
        
        .val-total { color: #fff; }
        .val-resolved { color: #4ade80; }
        .val-escalated { color: #60a5fa; }
        .val-clarification { color: #fbbf24; }
        .val-precision { color: #a78bfa; }
        .val-runtime { color: #2dd4bf; }

        .results-container {
            background: var(--sw-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--sw-border);
            border-radius: 20px;
            margin-top: 30px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        .table { margin-bottom: 0; }
        .table thead th { 
            background: rgba(255,255,255,0.02);
            color: #8b949e; font-weight: 600; text-transform: uppercase; font-size: 0.75rem;
            padding: 1.2rem 1rem; border-bottom: 1px solid var(--sw-border);
        }
        .table tbody td { padding: 1rem; border-bottom: 1px solid var(--sw-border); vertical-align: middle; }
        .table tbody tr:hover { background: rgba(255,255,255,0.02); }

        .badge-status { 
            padding: 6px 12px; border-radius: 8px; font-size: 0.75rem; font-weight: 700; 
            display: inline-flex; align-items: center; gap: 6px;
        }
        .bg-resolved { background: rgba(74, 222, 128, 0.1); color: #4ade80; border: 1px solid rgba(74, 222, 128, 0.2); }
        .bg-escalated { background: rgba(96, 165, 250, 0.1); color: #60a5fa; border: 1px solid rgba(96, 165, 250, 0.2); }
        .bg-clara { background: rgba(251, 191, 36, 0.1); color: #fbbf24; border: 1px solid rgba(251, 191, 36, 0.2); }
        .bg-fail { background: rgba(248, 113, 113, 0.1); color: #f87171; border: 1px solid rgba(248, 113, 113, 0.2); }

        .audit-modal .modal-content { 
            background: #0d1117; border: 1px solid var(--sw-border); border-radius: 20px;
            box-shadow: 0 0 50px rgba(0,0,0,0.5);
        }
        .audit-pre { 
            background: #010409; border: 1px solid var(--sw-border); border-radius: 12px; 
            padding: 20px; color: #4ade80; font-family: 'Fira Code', monospace;
            font-size: 0.85rem; max-height: 600px;
        }
        
        .pulse { animation: pulse 2s infinite; }
        @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.3; } }
        
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: var(--sw-bg); }
        ::-webkit-scrollbar-thumb { background: var(--sw-border); border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: #484f58; }
    </style>
</head>
<body>
    <nav class="navbar navbar-dark">
        <span class="navbar-brand brand-text">SHOPWAVE</span>
        <div class="d-flex align-items-center">
            <span class="badge bg-resolved me-3" id="liveTag" style="display:none; font-size: 0.65rem;">● SYSTEM LIVE</span>
            <span class="text-muted small">v2.1 Build Final</span>
        </div>
    </nav>

    <div class="container px-4">
        <div class="hero">
            <h1>Autonomous Triage</h1>
            <p>High-fidelity ticket resolution engine featuring deterministic guardrails and multi-step tool orchestration.</p>
            <div class="mt-4">
                <button class="btn btn-run btn-lg" onclick="runAgent()" id="runBtn">
                    Launch Resolution Cycle
                </button>
                <button class="btn btn-outline-secondary btn-lg ms-2" onclick="window.location.reload()" style="border-radius:12px; padding: 14px 30px;">
                    ↺ Reset
                </button>
            </div>
            <div id="runStatus" class="mt-3 text-muted small" style="height: 20px;"></div>
        </div>

        <!-- Metrics Cards -->
        <div class="row g-4 mb-5" id="metricsRow" style="display:none;">
            <div class="col-6 col-md-2"><div class="metric-card"><div class="metric-value val-total" id="mTotal">0</div><div class="metric-label">Processed</div></div></div>
            <div class="col-6 col-md-2"><div class="metric-card"><div class="metric-value val-resolved" id="mResolved">0</div><div class="metric-label">Resolved</div></div></div>
            <div class="col-6 col-md-2"><div class="metric-card"><div class="metric-value val-escalated" id="mEscalated">0</div><div class="metric-label">Escalated</div></div></div>
            <div class="col-6 col-md-2"><div class="metric-card"><div class="metric-value val-clarification" id="mClarification">0</div><div class="metric-label">Queries</div></div></div>
            <div class="col-6 col-md-2"><div class="metric-card"><div class="metric-value val-precision" id="mPrecision">100%</div><div class="metric-label">Precision</div></div></div>
            <div class="col-6 col-md-2"><div class="metric-card"><div class="metric-value val-runtime" id="mRuntime">0s</div><div class="metric-label">Latency</div></div></div>
        </div>

        <!-- Results Table -->
        <div class="results-container" id="resultsCard" style="display:none;">
            <table class="table">
                <thead><tr>
                    <th>Ticket ID</th><th>Customer</th><th>Intent</th><th>Safe Action</th>
                    <th>Tools</th><th>Cycle Time</th><th>Status</th><th>Audit</th>
                </tr></thead>
                <tbody id="resultsBody"></tbody>
            </table>
        </div>
    </div>

    <!-- Audit Modal -->
    <div class="modal fade audit-modal" id="auditModal" tabindex="-1">
        <div class="modal-dialog modal-xl modal-dialog-centered">
            <div class="modal-content">
                <div class="modal-header border-0 pb-0">
                    <h5 class="modal-title brand-text" id="auditTitle">Audit Trace</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <pre class="audit-pre" id="auditContent"></pre>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        let currentJobId = null;
        let pollInterval = null;

        async function runAgent() {
            const btn = document.getElementById('runBtn');
            btn.disabled = true;
            btn.textContent = 'Processing...';
            document.getElementById('runStatus').innerHTML = '<span class="pulse">Engine executing concurrent resolution chains...</span>';
            document.getElementById('liveTag').style.display = 'inline-flex';

            const res = await fetch('/run', { method: 'POST' });
            const data = await res.json();
            currentJobId = data.job_id;

            pollInterval = setInterval(pollStatus, 1000);
        }

        async function pollStatus() {
            if (!currentJobId) return;
            const res = await fetch('/status/' + currentJobId);
            const data = await res.json();

            if (data.status === 'complete') {
                clearInterval(pollInterval);
                document.getElementById('runBtn').disabled = false;
                document.getElementById('runBtn').textContent = 'Relaunch Cycle';
                document.getElementById('runStatus').textContent = 'Resolution cycle successfully completed.';
                renderResults(data);
            }
        }

        function renderResults(data) {
            document.getElementById('metricsRow').style.display = 'flex';
            document.getElementById('resultsCard').style.display = 'block';

            const m = data.metrics;
            document.getElementById('mTotal').textContent = m.ticket_count;
            document.getElementById('mResolved').textContent = m.resolved;
            document.getElementById('mEscalated').textContent = m.escalated;
            document.getElementById('mClarification').textContent = m.clarification_sent;
            document.getElementById('mRuntime').textContent = data.runtime + 's';

            const tbody = document.getElementById('resultsBody');
            tbody.innerHTML = '';
            data.results.forEach(r => {
                const badgeClass = {
                    resolved: 'bg-resolved', escalated: 'bg-escalated',
                    clarification_sent: 'bg-clara', failed: 'bg-fail'
                }[r.status] || '';
                
                tbody.innerHTML += `<tr>
                    <td><strong>${r.ticket_id}</strong></td>
                    <td>${r.customer_name}</td>
                    <td><span class="text-info small fw-bold">${r.classification}</span></td>
                    <td><code>${r.recommended_action}</code></td>
                    <td><span class="badge bg-secondary">${r.tools_called.length}</span></td>
                    <td>${r.latency_ms}ms</td>
                    <td><span class="badge-status ${badgeClass}">${r.status}</span></td>
                    <td><button class="btn btn-sm btn-outline-info" onclick="showAudit('${r.ticket_id}')">Inspect</button></td>
                </tr>`;
            });
        }

        async function showAudit(ticketId) {
            const res = await fetch('/audit/' + ticketId);
            const data = await res.json();
            document.getElementById('auditTitle').textContent = 'Audit: ' + ticketId;
            document.getElementById('auditContent').textContent = JSON.stringify(data, null, 2);
            new bootstrap.Modal(document.getElementById('auditModal')).show();
        }
    </script>
</body>
</html>
"""


def _run_agent_sync(job_id):
    """Run the agent in a background thread."""
    import asyncio
    from services.data_service import DataService
    from services.context_enrichment import ContextEnrichmentEngine
    from agent.resolution_agent import ResolutionAgent
    from tools.resolution_tools import ResolutionTools

    async def _run():
        ds = DataService()
        enricher = ContextEnrichmentEngine(ds)
        tools = ResolutionTools(ds)
        agent = ResolutionAgent(tools)

        start = time.time()
        enriched = await asyncio.gather(*[enricher.enrich_ticket(t) for t in ds.tickets])
        results = await agent.process_all_tickets(enriched)
        runtime = round(time.time() - start, 2)

        agent.save_audit_log()

        _job_results[job_id] = {
            "status": "complete",
            "results": [r.model_dump(mode="json") for r in results],
            "metrics": agent.metrics,
            "runtime": runtime,
        }
        _job_status[job_id] = "complete"

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_run())


@app.route("/")
def index():
    return render_template_string(DASHBOARD_HTML)


@app.route("/run", methods=["POST"])
def run_agent():
    job_id = f"job-{int(time.time())}"
    _job_status[job_id] = "running"
    thread = threading.Thread(target=_run_agent_sync, args=(job_id,), daemon=True)
    thread.start()
    return jsonify({"job_id": job_id, "status": "started"})


@app.route("/status/<job_id>")
def get_status(job_id):
    if job_id in _job_results:
        return jsonify(_job_results[job_id])
    return jsonify({"status": _job_status.get(job_id, "unknown")})


@app.route("/audit/<ticket_id>")
def get_audit(ticket_id):
    try:
        with open("audit_log.json", "r") as f:
            logs = json.load(f)
        for log in logs:
            if log["ticket_id"] == ticket_id:
                return jsonify(log)
        return jsonify({"error": "Ticket not found"}), 404
    except FileNotFoundError:
        return jsonify({"error": "No audit log. Run agent first."}), 404


@app.route("/metrics")
def get_metrics():
    try:
        with open("audit_log.json", "r") as f:
            logs = json.load(f)
        total = len(logs)
        resolved = sum(1 for l in logs if l["status"] == "resolved")
        escalated = sum(1 for l in logs if l["status"] == "escalated")
        return jsonify({
            "total": total, "resolved": resolved, "escalated": escalated,
            "success_rate": f"{(resolved + escalated) / total * 100:.0f}%",
        })
    except FileNotFoundError:
        return jsonify({"error": "No audit log"}), 404


if __name__ == "__main__":
    print("Starting ShopWave Dashboard at http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
