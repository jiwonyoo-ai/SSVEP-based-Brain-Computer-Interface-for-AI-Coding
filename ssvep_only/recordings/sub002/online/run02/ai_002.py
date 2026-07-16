# 의도: 사용자 딕셔너리에서 ID로 사용자 정보를 검색하여 출력
users = {
    "U001": {"이름": "Alice", "나이": 30, "직책": "개발자"},
    "U002": {"이름": "Bob",   "나이": 25, "직책": "디자이너"},
    "U003": {"이름": "Carol", "나이": 28, "직책": "기획자"},
}

query = input("검색할 사용자 ID를 입력하세요 (예: U001): ").strip().upper()

if query in users:
    info = users[query]
    print(f"[검색 결과] ID: {query}")
    for key, value in info.items():
        print(f"  {key}: {value}")
else:
    print(f"ID '{query}'에 해당하는 사용자를 찾을 수 없습니다.")
