# 의도: 원의 넓이와 둘레를 계산하여 출력하는 코드 작성
import math

# 반지름 입력
radius = float(input("반지름을 입력하세요: "))

# 원의 넓이와 둘레 계산
area = math.pi * radius ** 2
circumference = 2 * math.pi * radius

print(f"반지름: {radius}")
print(f"원의 넓이: {area:.4f}")
print(f"원의 둘레: {circumference:.4f}")
