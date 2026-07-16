# 의도: Python 딕셔너리와 리스트를 활용해 간단한 인메모리 DB 구조를 직접 구현하는 코드

# 간단한 인메모리 데이터베이스 구현
class SimpleDB:
    def __init__(self):
        self.tables = {}

    def create_table(self, table_name, columns):
        self.tables[table_name] = {"columns": columns, "rows": []}
        print(f"테이블 '{table_name}' 생성 완료. 컬럼: {columns}")

    def insert(self, table_name, row):
        self.tables[table_name]["rows"].append(row)

    def select_all(self, table_name):
        table = self.tables[table_name]
        print(f"\n=== {table_name} 테이블 ===")
        print(" | ".join(table["columns"]))
        print("-" * 30)
        for row in table["rows"]:
            print(" | ".join(str(v) for v in row))

# 사용 예시
db = SimpleDB()
db.create_table("products", ["ID", "Name", "Price"])
db.insert("products", [1, "Apple", 1200])
db.insert("products", [2, "Banana", 800])
db.insert("products", [3, "Cherry", 3000])
db.select_all("products")
