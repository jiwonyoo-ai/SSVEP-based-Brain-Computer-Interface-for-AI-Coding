# 의도: 현재 인도 표준시(IST, UTC+5:30) 기준 시각을 출력하는 코드 작성
from datetime import datetime, timezone, timedelta

# IST는 UTC+5:30
ist_offset = timedelta(hours=5, minutes=30)
ist_tz = timezone(ist_offset)

now_ist = datetime.now(ist_tz)
print("현재 IST (인도 표준시):", now_ist.strftime("%Y-%m-%d %H:%M:%S %Z"))
