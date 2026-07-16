```python
# 의도: 콘솔에서 카운트다운 타이머 실행
import time

seconds = int(input("타이머 시간(초)를 입력하세요: "))
for i in range(seconds, 0, -1):
    print(f"\r남은 시간: {i:3d}초", end="", flush=True)
    time.sleep(1)
print("\r타이머 종료!          ")
```
