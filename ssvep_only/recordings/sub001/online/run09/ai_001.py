# 의도: 콘솔에 ASCII 아트로 원 모양을 출력하는 코드 작성
import math

# 원의 반지름 설정
radius = 10
for y in range(-radius, radius + 1):
    for x in range(-radius * 2, radius * 2 + 1):
        # 타원 비율 보정 (콘솔 폰트 비율 고려)
        if abs(math.sqrt((x / 2) ** 2 + y ** 2) - radius) < 1:
            print('*', end='')
        else:
            print(' ', end='')
    print()
