"""
test_ai_screen.py — ssvep_online 의 AI 화면만 단독 테스트
"print hi" 가 BCI 입력이라고 가정하고 AI 코드 생성 결과 화면을 띄움.

ssvep_online.py 와 동일한 _refine_intent prompt template 사용.
ssvep_online.py 는 전혀 건드리지 않음.

실행:
    cd C:\\EEG_Project\\final_ssvep\\ssvep_only
    python test_ai_screen.py
또는 다른 텍스트로:
    python test_ai_screen.py "make a list of 1 to 10"

조작:
    Esc : 종료
"""
import sys
import time
import pygame

from ai_coder import AICoder


# ssvep_online.py 와 동일한 색상/설정
BG_COLOR     = (30, 30, 30)
WHITE        = (240, 240, 240)
CYAN         = (80, 200, 200)
TARGET_COLOR = (255, 180, 80)
BRIGHT_TEXT  = (200, 200, 200)
GRAY         = (120, 120, 120)

SCREEN_W = 1500
SCREEN_H = 840


def refine_intent(text):
    """ssvep_online.py 의 _refine_intent (597줄) 와 동일"""
    return (
        "Python으로 다음 명령을 수행하는 코드 후보 2개를 작성해줘.\n"
        "두 후보는 반드시 서로 다른 접근 방식으로 작성해줘.\n"
        "1번은 가장 짧고 단순한 기본 구현으로 작성해줘.\n"
        "2번은 1번과 다른 구조나 실행 방식의 대안 구현으로 작성해줘.\n"
        "예를 들어 콘솔 출력 vs 함수화/GUI/파일 출력/웹 서버처럼 차이가 나야 해.\n"
        "변수명만 다른 거의 같은 코드는 만들지 마.\n"
        "반드시 아래 형식으로만 출력해줘.\n"
        "### CODE 1\n"
        "[첫 번째 Python 코드]\n"
        "### CODE 2\n"
        "[두 번째 Python 코드]\n"
        f"명령: {text}"
    )


def split_options(code):
    m1, m2 = "### CODE 1", "### CODE 2"
    if m1 in code and m2 in code:
        c1 = code.split(m1, 1)[1].split(m2, 1)[0].strip()
        c2 = code.split(m2, 1)[1].strip()
        return c1, c2
    return code, ""


def draw_wrapped(screen, text, font, color, x, y, max_w, line_h):
    words = text.split(" ")
    lines, current = [], ""
    for w in words:
        cand = w if not current else f"{current} {w}"
        if font.size(cand)[0] <= max_w:
            current = cand
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    for line in lines:
        surf = font.render(line, True, color)
        screen.blit(surf, (x, y))
        y += line_h
    return y


def draw_loading(screen, fonts, input_text, screen_w, screen_h):
    screen.fill(BG_COLOR)
    cx, cy = screen_w // 2, screen_h // 2
    content_w = min(screen_w - 220, 1280)
    content_x = screen_w // 2 - content_w // 2

    title = fonts["title"].render("AI 코드 생성 중...", True, CYAN)
    screen.blit(title, title.get_rect(center=(cx, cy - 100)))
    raw = fonts["text"].render(f"입력 문장: {input_text}", True, WHITE)
    screen.blit(raw, (content_x, cy - 18))
    draw_wrapped(
        screen, "코드 후보 2개를 생성하는 중입니다.",
        fonts["text"], TARGET_COLOR, content_x, cy + 30, content_w, 38,
    )


def draw_result(screen, fonts, input_text, code1, code2, screen_w, screen_h):
    screen.fill(BG_COLOR)
    cx = screen_w // 2
    content_w = min(screen_w - 220, 1280)
    content_x = screen_w // 2 - content_w // 2

    y = screen_h // 2 - 330
    title = fonts["title"].render("AI 코드 생성 완료", True, CYAN)
    screen.blit(title, title.get_rect(center=(cx, y)))
    y += 78

    raw = fonts["text"].render(f"입력 문장: {input_text}", True, WHITE)
    screen.blit(raw, (content_x, y))
    y += 48

    y = draw_wrapped(screen, "1번 코드", fonts["text"], TARGET_COLOR, content_x, y, content_w, 38)
    y = draw_wrapped(screen, "2번 코드", fonts["text"], TARGET_COLOR, content_x, y, content_w, 38)
    y += 36

    box_gap = 24
    box_y = y
    box_w = (content_w - box_gap) // 2
    box_h = max(260, screen_h - box_y - 92)
    line_h = 27

    def draw_code_box(idx, code):
        box_x = content_x + idx * (box_w + box_gap)
        pygame.draw.rect(screen, (24, 24, 24), (box_x, box_y, box_w, box_h), border_radius=8)
        pygame.draw.rect(screen, (95, 95, 95), (box_x, box_y, box_w, box_h), width=2, border_radius=8)

        header = fonts["med"].render(f"{idx + 1}번 코드", True, WHITE)
        screen.blit(header, (box_x + 24, box_y + 18))
        pygame.draw.line(screen, (75, 75, 75),
                         (box_x + 20, box_y + 58),
                         (box_x + box_w - 20, box_y + 58), 1)

        code_y = box_y + 76
        code_x = box_x + 24
        code_max_w = box_w - 48
        code_bottom = box_y + box_h - 24
        clip = pygame.Rect(code_x, code_y, code_max_w, max(0, code_bottom - code_y))
        old_clip = screen.get_clip()
        screen.set_clip(clip)
        for line in code.split("\n"):
            if code_y + line_h > code_bottom:
                screen.blit(fonts["code"].render("...", True, BRIGHT_TEXT),
                            (code_x, max(code_y, code_bottom - line_h)))
                break
            screen.blit(fonts["code"].render(line, True, BRIGHT_TEXT), (code_x, code_y))
            code_y += line_h
        screen.set_clip(old_clip)

    draw_code_box(0, code1)
    draw_code_box(1, code2)

    hint = fonts["med"].render("Esc=종료", True, GRAY)
    screen.blit(hint, hint.get_rect(center=(cx, screen_h - 30)))


def main():
    user_input = sys.argv[1] if len(sys.argv) > 1 else "print hi"

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("AI 코드 생성 화면 테스트")
    clock = pygame.time.Clock()

    fonts = {
        "title": pygame.font.SysFont("malgun gothic", 50, bold=True),
        "text":  pygame.font.SysFont("malgun gothic", 28),
        "med":   pygame.font.SysFont("malgun gothic", 24, bold=True),
        "code":  pygame.font.SysFont("consolas", 18),
    }

    ai = AICoder()
    ai.generate(refine_intent(user_input))

    code1, code2 = "", ""
    error_msg = None
    done = False

    while True:
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); return
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit(); return

        if not done:
            r = ai.get_result()
            if r is not None:
                if r.get("status") == "ok":
                    code1, code2 = split_options(r["code"])
                    if not code2:
                        code2 = "(2번 코드 분리 실패 — 1번에 전체)"
                else:
                    error_msg = r.get("msg", "알 수 없는 오류")
                    code1 = f"오류: {error_msg}"
                done = True

        if not done:
            draw_loading(screen, fonts, user_input, SCREEN_W, SCREEN_H)
        else:
            draw_result(screen, fonts, user_input, code1, code2, SCREEN_W, SCREEN_H)

        pygame.display.flip()


if __name__ == "__main__":
    main()