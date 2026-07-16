# 의도: Python으로 현재 시간을 실시간으로 표시하는 tkinter GUI 시계 생성

import tkinter as tk
from datetime import datetime

def update_time():
    # 현재 날짜와 시간 업데이트
    now = datetime.now()
    date_str = now.strftime("%Y년 %m월 %d일")
    time_str = now.strftime("%H:%M:%S")
    date_label.config(text=date_str)
    time_label.config(text=time_str)
    root.after(1000, update_time)  # 1초마다 갱신

# 메인 윈도우 설정
root = tk.Tk()
root.title("Time Site")
root.configure(bg="#1a1a2e")
root.geometry("400x200")

# 날짜 레이블
date_label = tk.Label(root, font=("Arial", 20), bg="#1a1a2e", fg="#a0a0ff")
date_label.pack(pady=(30, 5))

# 시간 레이블
time_label = tk.Label(root, font=("Arial", 48, "bold"), bg="#1a1a2e", fg="#00d4ff")
time_label.pack(pady=5)

# 시간 업데이트 시작
update_time()
root.mainloop()
