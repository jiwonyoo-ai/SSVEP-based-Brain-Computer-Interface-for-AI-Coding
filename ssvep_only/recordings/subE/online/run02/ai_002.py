# 의도: 이스라엘 표준시(IST, UTC+2) 기준 현재 시각과 주요 도시 정보를 출력하는 코드 작성
from datetime import datetime, timezone, timedelta

# IST (Israel Standard Time) = UTC+2
ist_offset = timedelta(hours=2)
ist_tz = timezone(ist_offset)

now_ist = datetime.now(ist_tz)

print("=" * 35)
print("  이스라엘 표준시 (IST, UTC+2)")
print("=" * 35)
print(f"  현재 시각 : {now_ist.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  대표 도시 : 예루살렘, 텔아비브")
print("=" * 35)
