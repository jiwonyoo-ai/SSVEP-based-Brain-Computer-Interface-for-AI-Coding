# 의도: 사용자로부터 여러 항목을 입력받아 리스트를 만들고 출력
items = []
n = int(input("리스트에 추가할 항목 수를 입력하세요: "))

for i in range(n):
    item = input(f"{i+1}번째 항목 입력: ")
    items.append(item)

print("\n생성된 리스트:", items)
print("정렬된 리스트:", sorted(items))
