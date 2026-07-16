# 의도: 사용자 정보 딕셔너리에서 ID로 사용자 이름을 검색하여 출력
users = {
    101: "Alice",
    202: "Bob",
    303: "Charlie",
    404: "Diana",
    505: "Eve"
}

try:
    search_id = int(input("검색할 사용자 ID를 입력하세요: "))
    if search_id in users:
        print(f"ID {search_id} → 사용자 이름: {users[search_id]}")
    else:
        print(f"ID {search_id} 에 해당하는 사용자가 없습니다.")
except ValueError:
    print("올바른 숫자 ID를 입력하세요.")
