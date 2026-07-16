# 의도: Python에서 SQLite를 사용해 간단한 데이터베이스를 생성하고 기본 테이블을 만드는 코드
import sqlite3

# SQLite 데이터베이스 생성 (메모리 내 실행)
conn = sqlite3.connect(":memory:")
cursor = conn.cursor()

# 기본 테이블 생성
cursor.execute("""
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        age INTEGER
    )
""")

# 샘플 데이터 삽입
sample_data = [("Alice", 30), ("Bob", 25), ("Charlie", 35)]
cursor.executemany("INSERT INTO users (name, age) VALUES (?, ?)", sample_data)
conn.commit()

# 데이터 조회 및 출력
print("=== users 테이블 데이터 ===")
cursor.execute("SELECT * FROM users")
for row in cursor.fetchall():
    print(f"ID: {row[0]}, 이름: {row[1]}, 나이: {row[2]}")

conn.close()
