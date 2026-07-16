```python
# 의도: 현재 시간을 실시간으로 콘솔에 출력하는 타임 사이트 대체 프로그램
import time

while True:
    # 현재 날짜와 시간 출력
    print(f"\r현재 시간: {time.strftime('%Y-%m-%d %H:%M:%S')}", end="", flush=True)
    time.sleep(1)
```
