```python
# 의도: 0과 1로 구성된 리스트 [0, 0, 1, 1]를 함수로 생성하고 상세 정보 출력
def make_list0011():
    # 패턴 문자열에서 리스트 생성
    pattern = "0011"
    result = [int(ch) for ch in pattern]
    return result

if __name__ == "__main__":
    lst = make_list0011()
    print(f"생성된 리스트: {lst}")
    print(f"길이: {len(lst)}")
    print(f"0의 개수: {lst.count(0)}, 1의 개수: {lst.count(1)}")
```
