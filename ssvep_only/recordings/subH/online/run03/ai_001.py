# 의도: 현재 시간을 보여주는 간단한 시계를 콘솔에 출력
import time

while True:
    # 현재 시간을 가져와 출력
    current_time = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"\r현재 시간: {current_time}", end="", flush=True)
    time.sleep(1)
