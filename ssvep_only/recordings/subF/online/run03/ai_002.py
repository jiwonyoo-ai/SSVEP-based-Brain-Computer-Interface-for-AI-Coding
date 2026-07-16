# 의도: 특정 시간 간격마다 현재 시각을 반복 출력하는 타이머 코드 작성
import time
import datetime

# 5초 간격으로 5번 현재 시각 출력
count = 5
for i in range(count):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    print(f"[{i+1}/{count}] 현재 시각: {now}")
    if i < count - 1:
        time.sleep(5)
