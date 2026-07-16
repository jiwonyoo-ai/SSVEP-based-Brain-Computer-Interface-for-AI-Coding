# 의도: 문자열에서 특정 문자 'T'를 검색하여 위치를 출력하는 코드 작성
text = "The quick brown fox jumps over the lazy dog"
target = 'T'

# 대소문자 구분 없이 'T' 문자 검색
positions = [i for i, ch in enumerate(text) if ch.upper() == target.upper()]

if positions:
    print(f"'{target}' 문자가 발견된 위치: {positions}")
    for pos in positions:
        print(f"  index {pos}: ...{text[max(0,pos-3):pos+4]}...")
else:
    print(f"'{target}' 문자를 찾을 수 없습니다.")
