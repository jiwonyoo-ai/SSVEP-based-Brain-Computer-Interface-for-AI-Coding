# 의도: 리스트 데이터를 보기 좋은 텍스트 테이블 형식으로 콘솔에 출력
headers = ["이름", "나이", "직업"]
rows = [
    ["Alice", 30, "Engineer"],
    ["Bob",   25, "Designer"],
    ["Carol", 28, "Manager"],
]

# 각 열의 최대 너비 계산
col_widths = [max(len(str(row[i])) for row in [headers] + rows) for i in range(len(headers))]

sep = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
def fmt_row(row):
    return "|" + "|".join(f" {str(v):<{col_widths[i]}} " for i, v in enumerate(row)) + "|"

print(sep)
print(fmt_row(headers))
print(sep)
for row in rows:
    print(fmt_row(row))
print(sep)
