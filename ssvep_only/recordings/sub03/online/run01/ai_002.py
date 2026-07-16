```python
# 의도: "HI" 문자열을 GUI 창에 표시
import tkinter as tk

# 메인 윈도우 생성
root = tk.Tk()
root.title("인사")
root.geometry("200x100")

# HI 텍스트 라벨 추가
label = tk.Label(root, text="HI", font=("Arial", 36, "bold"))
label.pack(expand=True)

root.mainloop()
```
