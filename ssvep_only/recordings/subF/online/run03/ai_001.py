# 의도: 현재 시간을 보여주는 간단한 타임스탬프 출력 코드 작성
import datetime

# 현재 날짜와 시간 출력
now = datetime.datetime.now()
print("현재 시간:", now.strftime("%Y-%m-%d %H:%M:%S"))
