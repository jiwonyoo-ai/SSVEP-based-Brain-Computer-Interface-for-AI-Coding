# 의도: 특정 사이트(URL)의 응답 시간(접속 소요 시간)을 측정하여 출력
import urllib.request
import time

# 측정할 URL 목록
urls = [
    "https://www.google.com",
    "https://www.github.com",
    "https://www.python.org"
]

for url in urls:
    try:
        start = time.time()
        urllib.request.urlopen(url, timeout=5)
        elapsed = time.time() - start
        print(f"{url} → 응답 시간: {elapsed:.3f}초")
    except Exception as e:
        print(f"{url} → 접속 실패: {e}")
