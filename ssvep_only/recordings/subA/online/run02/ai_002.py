```python
# 의도: 011로 시작하는 리스트 생성 및 출력 (함수화 구조)
def make_list011(start=1, count=10):
    result = []
    for i in range(start, start + count):
        result.append(f"011{i:03d}")
    return result

if __name__ == "__main__":
    data = make_list011()
    for item in data:
        print(item)
```
