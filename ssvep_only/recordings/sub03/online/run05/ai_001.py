```python
# 의도: 현재 시간을 표시하는 간단한 웹 페이지(타임 사이트) 생성
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

class TimeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 현재 시간 가져오기
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        html = f"<html><body><h1>현재 시간</h1><p>{now}</p></body></html>"
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))
    def log_message(self, format, *args):
        pass  # 로그 출력 억제

print("서버 시작: http://localhost:8080")
HTTPServer(("", 8080), TimeHandler).serve_forever()
```
