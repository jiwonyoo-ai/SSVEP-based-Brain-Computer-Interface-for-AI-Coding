```python
# 의도: 현재 시간을 자동 갱신하는 타임 사이트를 HTML 파일로 생성
from datetime import datetime
import os

# HTML 파일 경로
filename = "timesite.html"

# 자동 갱신되는 시계 HTML 페이지 작성
html_content = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>Time Site</title>
    <style>
        body { display: flex; justify-content: center; align-items: center;
               height: 100vh; margin: 0; background: #1a1a2e; color: #eaeaea;
               font-family: 'Courier New', monospace; flex-direction: column; }
        h1   { font-size: 2rem; color: #e94560; margin-bottom: 20px; }
        #clock { font-size: 4rem; letter-spacing: 4px; color: #0f3460; 
                 background: #eaeaea; padding: 20px 40px; border-radius: 12px; }
        #date  { font-size: 1.5rem; margin-top: 20px; color: #a8dadc; }
    </style>
</head>
<body>
    <h1>🕐 Time Site</h1>
    <div id="clock">00:00:00</div>
    <div id="date"></div>
    <script>
        function updateTime() {
            const now = new Date();
            document.getElementById('clock').textContent =
                now.toLocaleTimeString('ko-KR', {hour12: false});
            document.getElementById('date').textContent =
                now.toLocaleDateString('ko-KR', {year:'numeric', month:'long', day:'numeric', weekday:'long'});
        }
        updateTime();
        setInterval(updateTime, 1000);
    </script>
</body>
</html>
"""

# 파일 저장 및 브라우저에서 열기
with open(filename, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"'{filename}' 파일이 생성되었습니다. 브라우저로 열어주세요.")
os.startfile(filename)  # Windows 자동 실행 (Mac/Linux: os.system(f"open {filename}"))
```
