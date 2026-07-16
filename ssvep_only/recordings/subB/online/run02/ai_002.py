```python
# 의도: 0과 1로만 구성된 리스트 생성 및 출력 (함수화 + 반복 구조 변경)
import random

def make_binary_list(size=10):
    result = []
    for _ in range(size):
        result.append(random.choice([0, 1]))  # 0 또는 1 무작위 선택
    return result

if __name__ == "__main__":
    binary_list = make_binary_list()
    print("생성된 리스트:", binary_list)
    print("0의 개수:", binary_list.count(0))
    print("1의 개수:", binary_list.count(1))
```
