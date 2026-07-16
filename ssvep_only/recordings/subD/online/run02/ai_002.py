# 의도: 011로 끝나는 이름(LIST011)처럼 번호가 붙은 리스트 항목 11개를 생성하여 출력
my_list = [f"LIST{str(i).zfill(3)}" for i in range(1, 12)]
print(my_list)
