# 의도: 사용자로부터 ID를 입력받아 리스트에서 해당 ID를 검색하고 결과를 출력
id_list = [101, 202, 303, 404, 505]

target = int(input("검색할 ID를 입력하세요: "))

if target in id_list:
    print(f"ID {target} 을(를) 찾았습니다. (인덱스: {id_list.index(target)})")
else:
    print(f"ID {target} 을(를) 찾을 수 없습니다.")
