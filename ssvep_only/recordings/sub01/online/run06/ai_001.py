# 의도: Python으로 현재 시간을 표시하는 간단한 웹 페이지(로컬 서버) 생성

from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

class TimeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 현재 시간 가져오기
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="1">
    <title>Time Site</title>
    <style>
        body {{ display: flex; justify-content: center; align-items: center;
                height: 100vh; margin: 0; background: #1a1a2e; color: #e0e0e0;
                font-family: Arial, sans-serif; }}
        h1 {{ font-size: 3em; color: #00d4ff; }}
    </style>
</head>
<body>
    <div style="text-align:center;">
        <h1>🕐 현재 시간</h1>
        <p style="font-size:2em;">{now}</p>
    </div>
</body>
</html>"""
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format, *args):
        pass  # 로그 출력 억제

# 서버 시작
server = HTTPServer(("localhost", 8080), TimeHandler)
print("서버 실행 중: http://localhost:8080  (종료: Ctrl+C)")
server.serve_forever()
