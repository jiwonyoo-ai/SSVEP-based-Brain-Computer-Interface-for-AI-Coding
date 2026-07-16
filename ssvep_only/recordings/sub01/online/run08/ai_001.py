# 의도: 사용자로부터 ID를 입력받아 목록에서 해당 ID를 검색하여 결과를 출력
id_list = [101, 202, 303, 404, 505]

search_id = int(input("검색할 ID를 입력하세요: "))

if search_id in id_list:
    print(f"ID {search_id} 를 찾았습니다.")
else:
    print(f"ID {search_id} 를 찾을 수 없습니다.")
