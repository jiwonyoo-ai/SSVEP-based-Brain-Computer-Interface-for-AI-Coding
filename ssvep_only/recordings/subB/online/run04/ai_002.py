```python
# 의도: 함수 구조와 formatted 시:분:초 형식으로 카운트다운 타이머 실행
import time

def format_time(seconds):
    # 초를 시:분:초 형식으로 변환
    h, remainder = divmod(seconds, 3600)
    m, s = divmod(remainder, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def run_timer(total_seconds):
    # 카운트다운 실행
    remaining = total_seconds
    while remaining >= 0:
        print(f"\r⏱ 남은 시간: {format_time(remaining)}", end="", flush=True)
        time.sleep(1)
        remaining -= 1
    print("\n🔔 타이머 종료!")

def main():
    try:
        sec = int(input("타이머 시간(초)를 입력하세요: "))
        if sec <= 0:
            print("0보다 큰 숫자를 입력하세요.")
        else:
            run_timer(sec)
    except ValueError:
        print("숫자를 입력하세요.")

main()
```
