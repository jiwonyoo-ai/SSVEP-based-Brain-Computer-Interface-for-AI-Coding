# 의도: 011 패턴(0과 1로 구성)을 반복하여 길이 11의 리스트 생성 및 출력
pattern = [0, 1, 1]
my_list = [pattern[i % len(pattern)] for i in range(11)]
print(my_list)
