# 의도: 사용자로부터 문자열 목록을 입력받아 'T'로 시작하는 항목을 검색하여 출력하는 코드 작성
words = ["Tiger", "Apple", "Tree", "Banana", "Tokyo", "Sun", "Train", "Cat"]
target_prefix = 'T'

# 'T'로 시작하는 단어 검색
results = [w for w in words if w.upper().startswith(target_prefix.upper())]

print(f"'{target_prefix}'로 시작하는 단어 검색 결과:")
if results:
    for r in results:
        print(f"  - {r}")
else:
    print("  검색 결과 없음")
