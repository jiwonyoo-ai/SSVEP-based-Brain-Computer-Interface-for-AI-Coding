```python
# 의도: 구구단 곱셈표(테이블)를 콘솔에 출력

print("   " + "  ".join(f"{i:2}" for i in range(1, 10)))
print("-" * 30)
for i in range(1, 10):
    row = f"{i} |" + "  ".join(f"{i*j:2}" for j in range(1, 10))
    print(row)
```
