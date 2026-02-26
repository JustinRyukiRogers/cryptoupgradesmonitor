from http.server import BaseHTTPRequestHandler
import sys
import os

# Add the project root to the Python path so Vercel can find `src`
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.main import main

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            print("Cron Triggered: Starting Monitor Cycle...")
            # Execute the main monitor logic
            main()
            
            # Send Success Response
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write("Cron cycle completed successfully.".encode('utf-8'))
            
        except Exception as e:
            # Send Error Response
            self.send_response(500)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"Cron cycle failed: {str(e)}".encode('utf-8'))
            print(f"CRON ERROR: {e}")
