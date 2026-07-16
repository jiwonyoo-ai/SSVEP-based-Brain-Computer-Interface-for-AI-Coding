# 의도: 현재 시각부터 경과 시간을 측정하는 스톱워치를 콘솔에서 실행하는 코드 작성
import time

print("스톱워치 시작! 멈추려면 Ctrl+C를 누르세요.\n")
start = time.time()

try:
    while True:
        elapsed = time.time() - start
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        millis = int((elapsed % 1) * 100)
        print(f"  경과 시간: {mins:02d}:{secs:02d}.{millis:02d}", end="\r")
        time.sleep(0.05)
except KeyboardInterrupt:
    elapsed = time.time() - start
    mins = int(elapsed // 60)
    secs = int(elapsed % 60)
    print(f"\n\n⏹ 정지! 최종 경과 시간: {mins:02d}분 {secs:02d}초")
