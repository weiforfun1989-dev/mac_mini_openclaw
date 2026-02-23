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
import sys
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
    
    def do_POST(self):
        parsed = urlparse(self.path)
        
        # API endpoint to confirm a job
        if parsed.path == '/api/confirm':
            self.handle_confirm()
            return
        
        self.send_error(404, "Not found")
    
    def handle_confirm(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            job_id = data.get('job_id')
            auto_dispatch = data.get('dispatch', False)
            
            if not job_id:
                self.send_json_error("Missing job_id", 400)
                return
            
            # Load and update job
            sys.path.insert(0, str(Path(__file__).parent))
            from jobs import load_db, get_job, save_db
            
            db = load_db()
            job = get_job(db, job_id)
            
            if not job:
                self.send_json_error("Job not found", 404)
                return
            
            if not job.get("needs_confirmation"):
                self.send_json_error("Job doesn't need confirmation", 400)
                return
            
            if job.get("confirmed"):
                self.send_json_error("Job already confirmed", 400)
                return
            
            # Confirm the job
            from datetime import datetime
            job["confirmed"] = True
            job["confirmed_at"] = datetime.now().isoformat()
            job["notes"] = "Confirmed via dashboard"
            save_db(db)
            
            # Auto-dispatch if requested
            if auto_dispatch:
                from workflow import dispatch_to_agent
                try:
                    dispatch_to_agent(job_id, "research")
                    dispatch_result = "Dispatched to Sage"
                except Exception as e:
                    dispatch_result = f"Dispatch failed: {e}"
            else:
                dispatch_result = None
            
            response = json.dumps({
                "success": True,
                "job_id": job_id,
                "dispatch_result": dispatch_result
            }).encode('utf-8')
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Content-Length', str(len(response)))
            self.end_headers()
            self.wfile.write(response)
            
        except Exception as e:
            self.send_json_error(str(e), 500)
    
    def send_json_error(self, message, status_code):
        error = json.dumps({"error": message}).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(error)
        # Suppress request logging
        pass

def start_server():
    """Start the dashboard server."""
    # Allow address reuse to prevent "Address already in use" errors
    socketserver.TCPServer.allow_reuse_address = True
    
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