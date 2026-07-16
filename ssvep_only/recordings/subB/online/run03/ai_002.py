```python
# 의도: 현재 시간을 실시간으로 콘솔에 출력하는 타임 사이트 대체 프로그램
import time
from datetime import datetime

def get_time_info():
    # 현재 시간 정보를 딕셔너리로 반환
    now = datetime.now()
    return {
        "날짜": now.strftime("%Y년 %m월 %d일"),
        "시간": now.strftime("%H시 %M분 %S초"),
        "요일": ["월", "화", "수", "목", "금", "토", "일"][now.weekday()] + "요일",
    }

def display_clock():
    print("=== 실시간 시계 시작 (종료: Ctrl+C) ===")
    try:
        while True:
            info = get_time_info()
            # 화면 초기화 후 시간 정보 출력
            print("\033[H\033[J", end="")
            for key, value in info.items():
                print(f"  {key}: {value}")
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n시계를 종료합니다.")

if __name__ == "__main__":
    display_clock()
```
