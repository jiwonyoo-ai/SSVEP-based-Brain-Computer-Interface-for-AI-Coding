```python
# 의도: 구구단 곱셈표(테이블)를 함수와 리스트로 구성하여 콘솔에 출력

def make_table(size=9):
    # 헤더 행 생성
    header = ["   "] + [f"{j:3}" for j in range(1, size + 1)]
    print("".join(header))
    print("-" * (3 + size * 3))

    # 각 행을 리스트로 구성 후 출력
    table = [[i * j for j in range(1, size + 1)] for i in range(1, size + 1)]
    for i, row in enumerate(table, start=1):
        print(f"{i} |" + "".join(f"{val:3}" for val in row))

if __name__ == "__main__":
    make_table()
```
