# 의도: 다양한 인사말 목록 중 "HI"를 포함한 여러 언어의 인사말을 출력하는 코드 작성
greetings = {"English": "HI", "Korean": "안녕하세요", "Spanish": "Hola", "Japanese": "こんにちは", "French": "Bonjour"}
for lang, greeting in greetings.items():
    print(f"[{lang}] {greeting}")
