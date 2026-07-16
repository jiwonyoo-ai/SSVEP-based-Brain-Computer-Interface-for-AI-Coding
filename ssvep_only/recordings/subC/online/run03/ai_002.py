```python
# 의도: 현재 시간을 실시간으로 콘솔에 출력하는 시계 프로그램 작성
import time
from datetime import datetime

def display_clock():
    # 1초 간격으로 현재 날짜와 시간을 출력하는 루프
    print("실시간 시계를 시작합니다. 종료하려면 Ctrl+C를 누르세요.")
    try:
        while True:
            now = datetime.now()
            time_info = {
                "날짜": now.strftime("%Y-%m-%d"),
                "시간": now.strftime("%H:%M:%S"),
                "요일": now.strftime("%A"),
            }
            # 콘솔 화면 초기화 후 출력
            print("\033[H\033[J", end="")
            for key, value in time_info.items():
                print(f"  {key}: {value}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n시계를 종료합니다.")

if __name__ == "__main__":
    display_clock()
```
