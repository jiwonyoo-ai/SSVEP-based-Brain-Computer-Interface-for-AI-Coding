# 의도: 현재 시간을 출력하는 간단한 타임스탬프 코드 작성
from datetime import datetime

# 현재 날짜와 시간 출력
now = datetime.now()
print("현재 시각:", now.strftime("%Y-%m-%d %H:%M:%S"))
