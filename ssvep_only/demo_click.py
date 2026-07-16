"""
demo_click.py — 피실험자용 클릭 기반 BCI 데모
=================================================================
[목적]
  실제 BCI 실험 전 피실험자에게 메뉴 구조와 동작 방식을 이해시키기 위한
  클릭 기반 데모. 뇌파 대신 마우스 클릭으로 동작.

[실행]
  python demo_click.py

[메뉴 구조]
  홈: 명령문 / 의문문 / 직접입력 / 기능키
  명령문: Make / Print / Search / 뒤로
  의문문: How to / What is / Why / 뒤로
  직접입력: 숫자,괄호 / 알파벳,/ / ~ / 뒤로
  기능키: 스페이스 / 지우기 / 실행 / 뒤로
"""

import math
import os
import time

import pygame
from ai_coder import AICoder

# ============================================================
# 화면 상수
# ============================================================
FRAME_RATE = 60
WINDOW_POS_X = 0
WINDOW_POS_Y = 0
BG_COLOR     = (30, 30, 30)
DIM_RECT     = (60, 60, 60)
HOVER_RECT   = (90, 90, 110)
CLICK_RECT   = (60, 120, 60)
BRIGHT_TEXT  = (200, 200, 200)
LINE_COLOR   = (50, 50, 50)
WHITE        = (240, 240, 240)
GREEN        = (80, 200, 80)
CYAN         = (80, 200, 200)
GRAY         = (120, 120, 120)
TARGET_COLOR = (255, 180, 80)

PREPARE_SEC   = 3.0
FEEDBACK_SEC  = 1.5
AI_REVIEW_SEC = 20.0


def get_window_size():
    pygame.display.init()
    info = pygame.display.Info()
    w = info.current_w if info.current_w > 0 else 1500
    h = info.current_h - 140 if info.current_h > 0 else 840
    return w, max(700, min(840, h))


# ============================================================
# 메뉴 트리
# ============================================================
_MENU_TREE = {
    "kind": "submenu",
    "options": ["명령문", "의문문", "직접입력", "기능키"],
    "descriptions": ["Make / Print / Search", "How to / What is / Why", "숫자 / 알파벳", "스페이스 / 지우기 / 실행"],
    "children": [
        # 0 명령문
        {
            "kind": "leaf_phrase",
            "options": ["Make", "Print", "Search", "뒤로"],
            "descriptions": ["", "", "", ""],
        },
        # 1 의문문
        {
            "kind": "leaf_phrase",
            "options": ["How to", "What is", "Why", "뒤로"],
            "descriptions": ["", "", "", ""],
        },
        # 2 직접입력
        {
            "kind": "direct_input",
            "options": ["숫자,괄호", "알파벳,/", "~", "뒤로"],
            "descriptions": ["", "", "", "전 화면으로"],
            "children": [
                # 2-0 숫자,괄호
                {
                    "kind": "submenu",
                    "options": ["0~2", "3~5", "6~8", "9/뒤로"],
                    "descriptions": ["0 1 2", "3 4 5", "6 7 8", "9 ( )"],
                    "children": [
                        {"kind": "leaf_letter", "options": ["0", "1", "2", "뒤로"], "descriptions": ["","","",""], "return_path": [2]},
                        {"kind": "leaf_letter", "options": ["3", "4", "5", "뒤로"], "descriptions": ["","","",""], "return_path": [2]},
                        {"kind": "leaf_letter", "options": ["6", "7", "8", "뒤로"], "descriptions": ["","","",""], "return_path": [2]},
                        {"kind": "leaf_letter", "options": ["9", "(", ")", "뒤로"], "descriptions": ["","","","전 화면으로"], "return_path": [2]},
                    ],
                },
                # 2-1 알파벳,/
                {
                    "kind": "submenu",
                    "options": ["A~I", "J~R", "S~Z", "뒤로"],
                    "descriptions": ["A B C / D E F / G H I", "J K L / M N O / P Q R", "S T U / V W X / Y Z /", "전 화면으로"],
                    "children": [
                        {
                            "kind": "submenu",
                            "options": ["A~C", "D~F", "G~I", "뒤로"],
                            "descriptions": ["A B C", "D E F", "G H I", "전 화면으로"],
                            "children": [
                                {"kind": "leaf_letter", "options": ["A", "B", "C", "뒤로"], "descriptions": ["","","","전 화면으로"], "return_path": [2]},
                                {"kind": "leaf_letter", "options": ["D", "E", "F", "뒤로"], "descriptions": ["","","","전 화면으로"], "return_path": [2]},
                                {"kind": "leaf_letter", "options": ["G", "H", "I", "뒤로"], "descriptions": ["","","","전 화면으로"], "return_path": [2]},
                                None,
                            ],
                        },
                        {
                            "kind": "submenu",
                            "options": ["J~L", "M~O", "P~R", "뒤로"],
                            "descriptions": ["J K L", "M N O", "P Q R", "전 화면으로"],
                            "children": [
                                {"kind": "leaf_letter", "options": ["J", "K", "L", "뒤로"], "descriptions": ["","","","전 화면으로"], "return_path": [2]},
                                {"kind": "leaf_letter", "options": ["M", "N", "O", "뒤로"], "descriptions": ["","","","전 화면으로"], "return_path": [2]},
                                {"kind": "leaf_letter", "options": ["P", "Q", "R", "뒤로"], "descriptions": ["","","","전 화면으로"], "return_path": [2]},
                                None,
                            ],
                        },
                        {
                            "kind": "submenu",
                            "options": ["S~U", "V~X", "Y/Z", "뒤로"],
                            "descriptions": ["S T U", "V W X", "Y Z /", "전 화면으로"],
                            "children": [
                                {"kind": "leaf_letter", "options": ["S", "T", "U", "뒤로"], "descriptions": ["","","","전 화면으로"], "return_path": [2]},
                                {"kind": "leaf_letter", "options": ["V", "W", "X", "뒤로"], "descriptions": ["","","","전 화면으로"], "return_path": [2]},
                                {"kind": "leaf_letter", "options": ["Y", "Z", "/", "뒤로"], "descriptions": ["","","","전 화면으로"], "return_path": [2]},
                                None,
                            ],
                        },
                        None,
                    ],
                },
                None,
                None,
            ],
        },
        # 3 기능키
        {
            "kind": "leaf_function",
            "options": ["스페이스", "지우기", "실행", "뒤로"],
            "descriptions": ["", "", "", ""],
        },
    ],
}


# ============================================================
# MenuState
# ============================================================
class MenuState:
    def __init__(self):
        self.path: list = []
        self.output: str = ""

    def _node(self):
        n = _MENU_TREE
        for idx in self.path:
            n = n["children"][idx]
        return n

    @property
    def labels(self):
        return self._node()["options"]

    @property
    def descriptions(self):
        return self._node().get("descriptions", [""] * 4)

    def select(self, idx):
        node  = self._node()
        label = node["options"][idx]
        kind  = node.get("kind", "submenu")

        # 뒤로
        if label == "뒤로":
            if self.path:
                self.path.pop()
            return "back"

        # 기능키
        if kind == "leaf_function":
            if label == "스페이스":
                self.output += " "; self.path = []; return "space"
            if label == "지우기":
                if self.output: self.output = self.output[:-1]
                self.path = []; return "delete"
            if label == "실행":
                self.path = []; return "run"

        # 명령문/의문문 단어 선택
        if kind == "leaf_phrase":
            self.output += label + " "; self.path = []; return "phrase"

        if kind == "direct_input":
            if label == "~":
                self.output += "~"
                self.path = [2]
                return "char"

        # 글자 선택
        if kind == "leaf_letter":
            self.output += label
            self.path = list(node.get("return_path", []))
            return "char"

        # 서브메뉴 진입
        self.path.append(idx)
        return "navigate"

    def delete_last(self):
        if self.output:
            self.output = self.output[:-1]


# ============================================================
# DemoExperiment
# ============================================================
class DemoExperiment:
    def __init__(self):
        os.environ["SDL_VIDEO_WINDOW_POS"] = f"{WINDOW_POS_X},{WINDOW_POS_Y}"
        pygame.init()
        self.W, self.H = get_window_size()
        self.screen = pygame.display.set_mode((self.W, self.H))
        pygame.display.set_caption("BCI 데모 — 클릭으로 체험하기")
        self.clock = pygame.time.Clock()

        self.f_big   = pygame.font.SysFont("malgun gothic", 76, bold=True)
        self.f_desc  = pygame.font.SysFont("malgun gothic", 22)
        self.f_med   = pygame.font.SysFont("malgun gothic", 28, bold=True)
        self.f_sml   = pygame.font.SysFont("malgun gothic", 20)
        self.f_tiny  = pygame.font.SysFont("malgun gothic", 16)
        self.f_title = pygame.font.SysFont("malgun gothic", 48, bold=True)
        self.f_code  = pygame.font.SysFont("malgun gothic", 21)

        self.TOP    = 60
        self.BOT    = self.H - 28
        self.GH     = self.BOT - self.TOP
        self.CW     = self.W // 2 - 30
        self.CH     = self.GH // 2 - 30

        self.centers = [
            (self.W // 4,     self.TOP + self.GH // 4),
            (self.W * 3 // 4, self.TOP + self.GH // 4),
            (self.W // 4,     self.TOP + self.GH * 3 // 4),
            (self.W * 3 // 4, self.TOP + self.GH * 3 // 4),
        ]

        self.menu  = MenuState()
        self.ai    = AICoder()

        self.ai_loading         = False
        self.ai_result          = None
        self.ai_options         = []
        self.ai_intents         = []
        self.ai_review_start    = 0.0
        self.ai_input_text      = ""
        self.ai_selected_code   = ""
        self.ai_selected_intent = ""
        self.ai_choice_labels   = ["1번 코드", "2번 코드", "더 입력하기", "다시 보기"]

        self.phase          = "prepare"
        self.prepare_start  = time.time()
        self.feedback_text  = ""
        self.feedback_timer = 0.0
        self.click_quad     = -1

    # ── 헬퍼 ──
    def _rect(self, idx):
        cx, cy = self.centers[idx]
        return pygame.Rect(cx - self.CW // 2, cy - self.CH // 2, self.CW, self.CH)

    def _hovered(self, mx, my):
        for i in range(4):
            if self._rect(i).collidepoint(mx, my):
                return i
        return -1

    def _refine(self, text):
        return (
            "Python으로 다음 명령을 수행하는 코드 후보 2개를 작성해줘.\n"
            "두 후보는 반드시 서로 다른 접근 방식으로 작성해줘.\n"
            "1번은 가장 짧고 단순한 기본 구현으로 작성해줘.\n"
            "2번은 1번과 다른 구조나 실행 방식의 대안 구현으로 작성해줘.\n"
            "반드시 아래 형식으로만 출력해줘.\n"
            "### CODE 1\n[첫 번째 Python 코드]\n"
            "### CODE 2\n[두 번째 Python 코드]\n"
            f"명령: {text}"
        )

    def _split(self, code):
        m1, m2 = "### CODE 1", "### CODE 2"
        if m1 in code and m2 in code:
            p1 = code.split(m1, 1)[1].split(m2, 1)[0].strip()
            p2 = code.split(m2, 1)[1].strip()
            return [p1, p2]
        return [code.strip(), code.strip()]

    def _intent(self, code):
        for line in code.splitlines():
            s = line.strip()
            if s.startswith("# 의도:"):
                return s.split(":", 1)[1].strip()
        return self.ai_input_text

    # ── 그리기 ──
    def _grid(self):
        pygame.draw.line(self.screen, LINE_COLOR,
                         (self.W // 2, self.TOP), (self.W // 2, self.BOT), 3)
        pygame.draw.line(self.screen, LINE_COLOR,
                         (0, (self.TOP + self.BOT) // 2),
                         (self.W, (self.TOP + self.BOT) // 2), 3)

    def _quad(self, idx, hover=False, clicked=False):
        cx, cy = self.centers[idx]
        rect   = self._rect(idx)

        bg = CLICK_RECT if clicked else (HOVER_RECT if hover else DIM_RECT)
        pygame.draw.rect(self.screen, bg, rect, border_radius=14)
        if hover or clicked:
            pygame.draw.rect(self.screen, WHITE, rect, width=3, border_radius=14)

        if self.phase == "ai_choice":
            label = self.ai_choice_labels[idx]
            desc  = ""
        else:
            label = self.menu.labels[idx]
            desc  = self.menu.descriptions[idx]

        label_y = cy - 34 if desc else cy
        surf = self.f_big.render(label, True, BRIGHT_TEXT)
        self.screen.blit(surf, surf.get_rect(center=(cx, label_y)))

        if desc:
            y = cy + 30
            for line in desc.split("\n"):
                ds = self.f_desc.render(line, True, BRIGHT_TEXT)
                self.screen.blit(ds, ds.get_rect(center=(cx, y)))
                y += ds.get_height() + 4

    def _all(self, hover=-1, clicked=-1):
        self.screen.fill(BG_COLOR)
        self._grid()
        for i in range(4):
            self._quad(i, hover=(i == hover), clicked=(i == clicked))

    def _topbar(self):
        out  = self.menu.output.replace("\n", " ↵ ")[-80:]
        surf = self.f_med.render(f"입력: {out}|", True, WHITE)
        self.screen.blit(surf, (20, 14))

    def _botbar(self):
        hint = self.f_tiny.render("클릭으로 선택  |  Esc=종료  Backspace=삭제", True, GRAY)
        self.screen.blit(hint, (self.W - hint.get_width() - 16, self.BOT + 6))

    def _draw_ai(self):
        self.screen.fill(BG_COLOR)
        cx  = self.W // 2
        cw  = min(self.W - 200, 1280)
        cx0 = cx - cw // 2

        if self.ai_loading:
            t = self.f_title.render("AI 코드 생성 중...", True, CYAN)
            self.screen.blit(t, t.get_rect(center=(cx, self.H // 2 - 60)))
            r = self.f_med.render(f"입력: {self.ai_input_text}", True, WHITE)
            self.screen.blit(r, (cx0, self.H // 2))
            return

        t = self.f_title.render("AI 코드 생성 완료 — 잠시 후 선택 화면", True, CYAN)
        y = 28
        self.screen.blit(t, t.get_rect(center=(cx, y))); y += 62

        r = self.f_med.render(f"입력: {self.ai_input_text}", True, WHITE)
        self.screen.blit(r, (cx0, y)); y += 40

        for oi, intent in enumerate(self.ai_intents[:2]):
            s = self.f_med.render(f"{oi+1}번: {intent}", True, TARGET_COLOR)
            self.screen.blit(s, (cx0, y)); y += 34
        y += 14

        bg  = 20
        bw  = (cw - bg) // 2
        bh  = max(240, self.H - y - 52)
        lh  = 24
        opts = self.ai_options or [self.ai_result or "", ""]

        for oi, code in enumerate(opts[:2]):
            bx = cx0 + oi * (bw + bg)
            pygame.draw.rect(self.screen, (24, 24, 24), (bx, y, bw, bh), border_radius=8)
            pygame.draw.rect(self.screen, (80, 80, 80), (bx, y, bw, bh), width=2, border_radius=8)
            hdr = self.f_med.render(f"{oi+1}번 코드", True, WHITE)
            self.screen.blit(hdr, (bx + 16, y + 14))
            pygame.draw.line(self.screen, (70, 70, 70),
                             (bx + 12, y + 50), (bx + bw - 12, y + 50), 1)
            cy2  = y + 62
            clip = pygame.Rect(bx + 12, cy2, bw - 24, bh - 70)
            old  = self.screen.get_clip()
            self.screen.set_clip(clip)
            for line in code.split("\n"):
                if cy2 + lh > y + bh - 12: break
                s = self.f_code.render(line, True, BRIGHT_TEXT)
                self.screen.blit(s, (bx + 12, cy2))
                cy2 += lh
            self.screen.set_clip(old)

        rem = max(0, int(AI_REVIEW_SEC - (time.time() - self.ai_review_start)) + 1)
        h   = self.f_sml.render(f"{rem}초 후 코드 선택 화면", True, GRAY)
        self.screen.blit(h, h.get_rect(center=(cx, self.H - 22)))

    def _draw_selected(self):
        self.screen.fill(BG_COLOR)
        cx  = self.W // 2
        cw  = min(self.W - 200, 1280)
        cx0 = cx - cw // 2

        t = self.f_title.render("선택된 코드", True, CYAN)
        y = 28
        self.screen.blit(t, t.get_rect(center=(cx, y))); y += 62

        r = self.f_med.render(f"입력: {self.ai_input_text}", True, WHITE)
        self.screen.blit(r, (cx0, y)); y += 40

        s = self.f_med.render(f"선택: {self.ai_selected_intent}", True, TARGET_COLOR)
        self.screen.blit(s, (cx0, y)); y += 50

        bh = min(self.H - y - 52, 520)
        pygame.draw.rect(self.screen, (24, 24, 24), (cx0, y, cw, bh), border_radius=8)
        pygame.draw.rect(self.screen, (80, 80, 80), (cx0, y, cw, bh), width=2, border_radius=8)
        hdr = self.f_med.render("생성된 코드", True, WHITE)
        self.screen.blit(hdr, (cx0 + 20, y + 14))
        pygame.draw.line(self.screen, (70, 70, 70),
                         (cx0 + 16, y + 50), (cx0 + cw - 16, y + 50), 1)

        lh   = 24
        cy2  = y + 62
        clip = pygame.Rect(cx0 + 16, cy2, cw - 32, bh - 70)
        old  = self.screen.get_clip()
        self.screen.set_clip(clip)
        for line in self.ai_selected_code.split("\n"):
            if cy2 + lh > y + bh - 12: break
            s = self.f_code.render(line, True, BRIGHT_TEXT)
            self.screen.blit(s, (cx0 + 16, cy2))
            cy2 += lh
        self.screen.set_clip(old)

        h = self.f_med.render("아무 키나 누르면 처음으로", True, GRAY)
        self.screen.blit(h, h.get_rect(center=(cx, self.H - 22)))

    # ── 선택 처리 ──
    def _select(self, quad):
        labels = list(self.menu.labels)
        label  = labels[quad]
        result = self.menu.select(quad)

        if result == "run":
            self._go_ai(); return
        if result in ("char", "phrase"):
            self.feedback_text = f"입력: {label}"
        elif result == "space":
            self.feedback_text = "입력: 스페이스"
        elif result == "delete":
            self.feedback_text = "지우기"
        else:
            self.feedback_text = f"선택: {label}"

        self.feedback_timer = time.time()
        self.phase = "feedback"

    def _go_ai(self):
        self.phase              = "ai"
        self.ai_loading         = True
        self.ai_result          = None
        self.ai_options         = []
        self.ai_intents         = []
        self.ai_review_start    = 0.0
        self.ai_selected_code   = ""
        self.ai_selected_intent = ""
        text = self.menu.output.strip() or "Hello World 출력"
        self.ai_input_text      = text
        self.ai.generate(self._refine(text))

    def _ai_choice(self, quad):
        if quad == 0:
            self.ai_selected_code   = self.ai_options[0] if self.ai_options else (self.ai_result or "")
            self.ai_selected_intent = self.ai_intents[0] if self.ai_intents else self.ai_input_text
            self.phase = "ai_selected"
        elif quad == 1:
            self.ai_selected_code   = self.ai_options[1] if len(self.ai_options) > 1 else (self.ai_result or "")
            self.ai_selected_intent = self.ai_intents[1] if len(self.ai_intents) > 1 else self.ai_input_text
            self.phase = "ai_selected"
        elif quad == 2:
            self.menu.path = [2]
            self.phase = "ssvep"
        elif quad == 3:
            self.phase = "ai"
            self.ai_review_start = time.time()

    # ── 메인 루프 ──
    def run(self):
        while True:
            self.clock.tick(FRAME_RATE)
            mx, my = pygame.mouse.get_pos()

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); return
                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        pygame.quit(); return
                    if ev.key == pygame.K_BACKSPACE:
                        self.menu.delete_last()
                    if self.phase == "ai_selected":
                        self.menu.output = ""
                        self.menu.path   = []
                        self.phase = "ssvep"

                if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    if self.phase in ("ssvep", "ai_choice"):
                        q = self._hovered(mx, my)
                        if q != -1:
                            self.click_quad = q

                if ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                    if self.phase in ("ssvep", "ai_choice") and self.click_quad != -1:
                        q = self.click_quad
                        self.click_quad = -1
                        if self._rect(q).collidepoint(mx, my):
                            if self.phase == "ai_choice":
                                self._ai_choice(q)
                            else:
                                self._select(q)

            # AI 폴링
            if self.phase == "ai" and self.ai_loading:
                res = self.ai.get_result()
                if res:
                    self.ai_loading = False
                    if res.get("status") == "ok":
                        self.ai_result       = res["code"]
                        self.ai_options      = self._split(self.ai_result)
                        self.ai_intents      = [self._intent(c) for c in self.ai_options[:2]]
                        self.ai_review_start = time.time()
                    else:
                        self.ai_result       = f"오류: {res.get('msg','')}"
                        self.ai_options      = [self.ai_result, ""]
                        self.ai_intents      = [self.ai_input_text, ""]
                        self.ai_review_start = time.time()

            if (self.phase == "ai" and self.ai_result
                    and not self.ai_loading
                    and time.time() - self.ai_review_start >= AI_REVIEW_SEC):
                self.phase = "ai_choice"

            # ── 렌더링 ──
            if self.phase == "prepare":
                self.screen.fill(BG_COLOR)
                rem = max(1, math.ceil(PREPARE_SEC - (time.time() - self.prepare_start)))
                cx, cy = self.W // 2, self.H // 2
                t = self.f_big.render("BCI 데모", True, CYAN)
                self.screen.blit(t, t.get_rect(center=(cx, cy - 110)))
                g = self.f_med.render("원하는 칸을 마우스로 클릭해서 명령을 입력하세요", True, WHITE)
                self.screen.blit(g, g.get_rect(center=(cx, cy - 16)))
                c = self.f_title.render(f"{rem}초 후 시작", True, GRAY)
                self.screen.blit(c, c.get_rect(center=(cx, cy + 76)))
                if time.time() - self.prepare_start >= PREPARE_SEC:
                    self.phase = "ssvep"

            elif self.phase == "ssvep":
                hq = self._hovered(mx, my)
                self._all(hover=hq, clicked=self.click_quad)
                self._topbar()
                self._botbar()

            elif self.phase == "feedback":
                self._all()
                rem = max(1, math.ceil(FEEDBACK_SEC - (time.time() - self.feedback_timer)))
                cx  = self.W // 2
                cy  = (self.TOP + self.BOT) // 2
                s   = self.f_big.render(self.feedback_text, True, GREEN)
                self.screen.blit(s, s.get_rect(center=(cx, cy - 30)))
                d   = self.f_med.render(f"{rem}초 후 다음 화면", True, GRAY)
                self.screen.blit(d, d.get_rect(center=(cx, cy + 60)))
                self._topbar(); self._botbar()
                if time.time() - self.feedback_timer >= FEEDBACK_SEC:
                    self.phase = "ssvep"

            elif self.phase == "ai":
                self._draw_ai()

            elif self.phase == "ai_choice":
                hq = self._hovered(mx, my)
                self._all(hover=hq, clicked=self.click_quad)
                self._topbar(); self._botbar()

            elif self.phase == "ai_selected":
                self._draw_selected()

            pygame.display.flip()


if __name__ == "__main__":
    demo = DemoExperiment()
    demo.run()
