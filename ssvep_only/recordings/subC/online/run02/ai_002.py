```python
# 의도: 0과 1로 이루어진 리스트를 함수로 생성 및 출력
def make_list011():
    # 비트 패턴 "011"을 정수 리스트로 변환
    return [int(bit) for bit in "011"]

if __name__ == "__main__":
    result = make_list011()
    print(result)
```
