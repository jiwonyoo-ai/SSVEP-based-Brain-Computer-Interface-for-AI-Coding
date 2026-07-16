```python
# 의도: 현재 시간을 실시간으로 콘솔에 출력하는 시계 프로그램
import time
from datetime import datetime

def display_clock():
    print("실시간 시계를 시작합니다. 종료하려면 Ctrl+C를 누르세요.")
    try:
        while True:
            now = datetime.now()
            # 날짜와 시간 정보를 딕셔너리로 구성
            time_info = {
                "날짜": now.strftime("%Y년 %m월 %d일"),
                "시간": now.strftime("%H시 %M분 %S초"),
                "요일": ["월","화","수","목","금","토","일"][now.weekday()]
            }
            # 콘솔 한 줄 갱신
            display = " | ".join(f"{k}: {v}" for k, v in time_info.items())
            print(f"\r{display}", end="", flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n시계를 종료합니다.")

if __name__ == "__main__":
    display_clock()
```
