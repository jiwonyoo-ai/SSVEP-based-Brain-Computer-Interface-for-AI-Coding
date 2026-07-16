# 의도: 원(circle)의 기본 정보(반지름, 둘레, 넓이)를 계산하여 출력
import math

radius = float(input("반지름을 입력하세요: "))

circumference = 2 * math.pi * radius
area = math.pi * radius ** 2

print(f"반지름   : {radius}")
print(f"둘레     : {circumference:.4f}")
print(f"넓이     : {area:.4f}")
