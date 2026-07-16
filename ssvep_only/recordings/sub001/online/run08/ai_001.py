# 의도: 카운트다운 타이머를 콘솔에서 실행하는 코드 작성
import time

seconds = int(input("타이머 시간(초)을 입력하세요: "))

print(f"\n⏱ {seconds}초 카운트다운 시작!")
for i in range(seconds, 0, -1):
    print(f"  남은 시간: {i}초", end="\r")
    time.sleep(1)

print("\n⏰ 타이머 종료!")
