import http.server
import socketserver
import os

PORT = 8000

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Disable caching mostly for local development
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        return super().end_headers()

if __name__ == "__main__":
    Handler = CustomHTTPRequestHandler
    
    # Enable SO_REUSEADDR so that running serve.py frequently won't fail with 'address already in use'
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving at port {PORT}")
        print(f"Open http://localhost:{PORT}/web/ in your browser.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
