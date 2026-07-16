```python
# 의도: tkinter GUI로 별 모양을 그리는 코드
import tkinter as tk
import math

root = tk.Tk()
root.title("별 그리기")
canvas = tk.Canvas(root, width=300, height=300, bg="black")
canvas.pack()

# 별의 꼭짓점 좌표 계산 (5각별)
cx, cy, r_out, r_in = 150, 150, 120, 50
points = []
for i in range(10):
    angle = math.radians(i * 36 - 90)  # 36도 간격
    r = r_out if i % 2 == 0 else r_in   # 바깥/안쪽 반지름 교대
    points.append(cx + r * math.cos(angle))
    points.append(cy + r * math.sin(angle))

canvas.create_polygon(points, fill="yellow", outline="orange", width=2)
root.mainloop()
```
