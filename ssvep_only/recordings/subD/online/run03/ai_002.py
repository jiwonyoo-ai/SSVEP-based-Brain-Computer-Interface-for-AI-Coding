# 의도: 특정 시간대(타임존)별 현재 시각을 비교해서 출력하는 코드 작성
from datetime import datetime
import zoneinfo

# 주요 도시별 타임존 목록
timezones = {
    "Seoul": "Asia/Seoul",
    "New York": "America/New_York",
    "London": "Europe/London",
    "Tokyo": "Asia/Tokyo",
    "Sydney": "Australia/Sydney",
}

# 각 도시의 현재 시각 출력
for city, tz in timezones.items():
    local_time = datetime.now(zoneinfo.ZoneInfo(tz))
    print(f"{city:10s}: {local_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
