#!/usr/bin/env python3
"""
Dashboard Server for Job Dispatch Workflow
Serves the web dashboard and provides API endpoints.
"""

import json
import http.server
import socketserver
import threading
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

PORT = 8765
JOBS_DB = Path("/Users/wxia/.openclaw/workspace/jobs/jobs-db.json")
DASHBOARD_DIR = Path("/Users/wxia/.openclaw/workspace/jobs/dashboard")

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DASHBOARD_DIR), **kwargs)
    
    def do_GET(self):
        parsed = urlparse(self.path)
        
        # API endpoint for jobs data
        if parsed.path == '/api/jobs':
            self.send_json_response()
            return
        
        # Serve static files
        if parsed.path == '/':
            self.path = '/index.html'
        
        return super().do_GET()
    
    def send_json_response(self):
        try:
            if JOBS_DB.exists():
                with open(JOBS_DB) as f:
                    data = json.load(f)
            else:
                data = {"version": "1.0", "jobs": [], "lastJobId": 0}
            
            response = json.dumps(data).encode('utf-8')
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(response)))
            self.end_headers()
            self.wfile.write(response)
        except Exception as e:
            error = json.dumps({"error": str(e)}).encode('utf-8')
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(error)
    
    def log_message(self, format, *args):
        # Suppress request logging
        pass

def start_server():
    """Start the dashboard server."""
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        print(f"🚀 Dashboard server running at http://localhost:{PORT}")
        print("   Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n👋 Server stopped")

def open_dashboard():
    """Open the dashboard in the default browser."""
    url = f"http://localhost:{PORT}"
    print(f"🌐 Opening {url}")
    webbrowser.open(url)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--open":
        # Open in browser and start server
        open_dashboard()
        start_server()
    else:
        start_server()