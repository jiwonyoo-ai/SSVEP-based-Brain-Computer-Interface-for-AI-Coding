# 의도: 콘솔에서 별(*)로 원 모양의 아스키 아트를 출력
import math

radius = 10  # 원의 반지름 (문자 단위)

for y in range(-radius, radius + 1):
    row = ""
    for x in range(-radius * 2, radius * 2 + 1):
        # 타원 보정을 위해 x 좌표를 절반으로 축소하여 비교
        if abs(math.sqrt((x / 2) ** 2 + y ** 2) - radius) < 1.0:
            row += "*"
        else:
            row += " "
    print(row)
