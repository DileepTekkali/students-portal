import os
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# This is the handler format Vercel expects for Python serverless functions.
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            qs = parse_qs(urlparse(self.path).query)

            # Accept ?id=AIK256Q1A4412
            certificate_id = (qs.get("id") or [""])[0].strip()

            # You MUST set these in Vercel Environment Variables
            supabase_url = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
            bucket = os.environ.get("SUPABASE_BUCKET") or "photos"

            if not supabase_url:
                self._send_json(500, {
                    "ok": False,
                    "error": "Missing SUPABASE_URL in Vercel Environment Variables"
                })
                return

            # Health check (open /api without id)
            if not certificate_id:
                self._send_json(200, {
                    "ok": True,
                    "message": "Pass ?id=AIK256Q1A4412",
                    "example": f"{supabase_url}/storage/v1/object/public/{bucket}/AIK256Q1A4412.jpg"
                })
                return

            # Build public URL (bucket is public)
            image_url = f"{supabase_url}/storage/v1/object/public/{bucket}/{certificate_id}.jpg"

            self._send_json(200, {
                "ok": True,
                "certificate_id": certificate_id,
                "image_url": image_url
            })

        except Exception as e:
            self._send_json(500, {"ok": False, "error": str(e)})

    def _send_json(self, status_code: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

