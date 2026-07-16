```python
# 의도: 문자열을 대문자로 변환하여 출력 (함수화 및 문자 단위 처리)
def to_upper(text):
    # 각 문자를 순회하며 대문자로 변환
    return ''.join(chr(ord(c) - 32) if 'a' <= c <= 'z' else c for c in text)

def main():
    text = input("문자열 입력: ")
    print(to_upper(text))

if __name__ == "__main__":
    main()
```
