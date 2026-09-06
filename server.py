from flask import Flask, request, jsonify, render_template_string
import sqlite3
import json

app = Flask(__name__)
DB_NAME = "endpointhero.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS request_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            method TEXT,
            url TEXT,
            status_code INTEGER,
            dns_ms REAL,
            tcp_ms REAL,
            tls_ms REAL,
            ttfb_ms REAL,
            total_ms REAL,
            response_body TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS webhook_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT,
            headers TEXT,
            payload TEXT,
            curl_command TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

init_db()

@app.route("/api/log-request", methods=["POST"])
def log_request():
    data = request.json or {}
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT INTO request_logs (method, url, status_code, dns_ms, tcp_ms, tls_ms, ttfb_ms, total_ms, response_body)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("method", "GET"),
        data.get("url", ""),
        data.get("status_code", 200),
        data.get("dns_ms", 0.0),
        data.get("tcp_ms", 0.0),
        data.get("tls_ms", 0.0),
        data.get("ttfb_ms", 0.0),
        data.get("total_ms", 0.0),
        json.dumps(data.get("response_body", {}))
    ))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Request logged"})

@app.route("/api/log-webhook", methods=["POST"])
def log_webhook():
    data = request.json or {}
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        INSERT INTO webhook_logs (path, headers, payload, curl_command)
        VALUES (?, ?, ?, ?)
    """, (
        data.get("path", "/webhook"),
        json.dumps(data.get("headers", {})),
        json.dumps(data.get("payload", {})),
        data.get("curl_command", "")
    ))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Webhook logged"})

@app.route("/api/data", methods=["GET"])
def get_dashboard_data():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM request_logs ORDER BY id DESC LIMIT 10")
    requests = [dict(row) for row in c.fetchall()]
    c.execute("SELECT * FROM webhook_logs ORDER BY id DESC LIMIT 10")
    webhooks = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({"requests": requests, "webhooks": webhooks})

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Endpoint Hero — Observability DB</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #0d0b0e; color: #e2e8f0; font-family: monospace; }
        .hero-border { border-color: #801818; }
        .hero-bg { background-color: #1a0f12; }
    </style>
</head>
<body class="p-6">
    <div class="max-w-7xl mx-auto space-y-6">
        <header class="flex justify-between items-center border-b border-red-900/40 pb-4">
            <div>
                <h1 class="text-3xl font-black text-red-500 tracking-wider">⚡ ENDPOINT HERO DB UI</h1>
                <p class="text-xs text-gray-400">Live Request Inspector, Timing Engine & Webhook Replay Log</p>
            </div>
            <div class="flex items-center space-x-2">
                <span class="w-3 h-3 bg-emerald-500 rounded-full animate-pulse"></span>
                <span class="text-xs text-emerald-400">DATABASE SYNC ACTIVE</span>
            </div>
        </header>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div class="hero-bg border hero-border rounded-xl p-5 shadow-2xl">
                <h2 class="text-lg font-bold text-gray-200 mb-4 flex items-center gap-2">
                    <span class="text-red-500">◆</span> API Request & Latency Analysis
                </h2>
                <div id="requests-container" class="space-y-3 overflow-y-auto max-h-[600px]">
                    <p class="text-gray-500 text-sm">Listening for CLI requests...</p>
                </div>
            </div>

            <div class="hero-bg border hero-border rounded-xl p-5 shadow-2xl">
                <h2 class="text-lg font-bold text-gray-200 mb-4 flex items-center gap-2">
                    <span class="text-red-500">◆</span> Captured Webhooks & cURL Replay
                </h2>
                <div id="webhooks-container" class="space-y-3 overflow-y-auto max-h-[600px]">
                    <p class="text-gray-500 text-sm">Waiting for incoming webhooks on mock server...</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        async function fetchLogs() {
            try {
                const res = await fetch('/api/data');
                const data = await res.json();
                
                const reqBox = document.getElementById('requests-container');
                if (data.requests.length > 0) {
                    reqBox.innerHTML = data.requests.map(r => `
                        <div class="bg-black/50 border border-red-900/30 p-3.5 rounded-lg space-y-2">
                            <div class="flex justify-between items-center text-sm">
                                <span class="font-bold text-amber-400 bg-amber-950/40 px-2 py-0.5 rounded border border-amber-800/40">${r.method}</span>
                                <span class="truncate max-w-[260px] text-gray-300">${r.url}</span>
                                <span class="font-bold ${r.status_code >= 400 ? 'text-red-400' : 'text-emerald-400'}">${r.status_code}</span>
                            </div>
                            <div class="grid grid-cols-5 gap-1 text-[10px] text-center pt-2 border-t border-gray-800 text-gray-400">
                                <div>DNS: <span class="text-white">${r.dns_ms}ms</span></div>
                                <div>TCP: <span class="text-white">${r.tcp_ms}ms</span></div>
                                <div>TLS: <span class="text-white">${r.tls_ms}ms</span></div>
                                <div>TTFB: <span class="text-white">${r.ttfb_ms}ms</span></div>
                                <div class="font-bold text-red-400">TOTAL: ${r.total_ms}ms</div>
                            </div>
                        </div>
                    `).join('');
                }

                const hookBox = document.getElementById('webhooks-container');
                if (data.webhooks.length > 0) {
                    hookBox.innerHTML = data.webhooks.map(w => `
                        <div class="bg-black/50 border border-red-900/30 p-3.5 rounded-lg space-y-2">
                            <div class="flex justify-between items-center text-sm">
                                <span class="text-red-400 font-bold">${w.path}</span>
                                <span class="text-[11px] text-gray-500">${w.created_at}</span>
                            </div>
                            <pre class="bg-black/80 p-2 rounded text-[11px] text-emerald-400 overflow-x-auto">${w.payload}</pre>
                            <div class="pt-1">
                                <span class="text-[10px] text-gray-500 uppercase font-semibold">One-Click Replay:</span>
                                <pre class="bg-red-950/20 border border-red-900/30 p-1.5 rounded text-[10px] text-gray-300 select-all overflow-x-auto">${w.curl_command || 'curl -X POST http://localhost:8080' + w.path}</pre>
                            </div>
                        </div>
                    `).join('');
                }
            } catch (err) {
                console.error("Failed fetching live logs:", err);
            }
        }
        setInterval(fetchLogs, 1500);
        fetchLogs();
    </script>
</body>
</html>
"""

@app.route("/")
def dashboard():
    return render_template_string(DASHBOARD_HTML)

if __name__ == "__main__":
    app.run(port=5000, debug=True)