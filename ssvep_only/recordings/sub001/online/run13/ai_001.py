# 의도: 구구단 표(multiplication table)를 콘솔에 출력
print(f"{'':4}", end="")
for i in range(1, 10):
    print(f"{i:4}", end="")
print()
print("-" * 40)

for i in range(1, 10):
    print(f"{i:4}", end="")
    for j in range(1, 10):
        print(f"{i*j:4}", end="")
    print()
