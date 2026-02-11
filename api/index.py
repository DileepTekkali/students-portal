import os
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            qs = parse_qs(urlparse(self.path).query)
            certificate_id = (qs.get("id") or [""])[0].strip()

            # You can set these in Vercel Env Vars.
            # If not set, we default to your exact values.
            supabase_url = (os.environ.get("SUPABASE_URL") or "https://scvfcifruoqsjfzptwbf.supabase.co").rstrip("/")
            bucket = (os.environ.get("SUPABASE_BUCKET") or "photos").strip()
            prefix = (os.environ.get("SUPABASE_PREFIX") or "student_images").strip().strip("/")

            if not certificate_id:
                example = f"{supabase_url}/storage/v1/object/public/{bucket}/{prefix}/AIK256Q1A4412.jpg"
                return self._json(200, {
                    "ok": True,
                    "message": "Use /api?id=AIK256Q1A4412",
                    "example_public_url": example
                })

            # Build URL (public bucket)
            filename = f"{certificate_id}.jpg"
            object_path = f"{prefix}/{filename}" if prefix else filename
            image_url = f"{supabase_url}/storage/v1/object/public/{bucket}/{object_path}"

            return self._json(200, {
                "ok": True,
                "certificate_id": certificate_id,
                "image_url": image_url
            })

        except Exception as e:
            return self._json(500, {"ok": False, "error": str(e)})

    def _json(self, status_code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

