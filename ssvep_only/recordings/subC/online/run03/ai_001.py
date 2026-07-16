```python
# 의도: 현재 시간을 실시간으로 콘솔에 출력하는 시계 프로그램 작성
import time

while True:
    print("\r현재 시간:", time.strftime("%Y-%m-%d %H:%M:%S"), end="", flush=True)
    time.sleep(1)
```
