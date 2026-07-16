"""
ssvep_online.py — SSVEP 전용 Online BCI 모드
=================================================================

[구조]
  SSVEP 자극 -> FBCCA 디코딩 -> 문자 메뉴 -> AI 코드 생성

[변경 사항]
  - P300 단계 완전 제거
  - 4분면 자극 화면은 Training 모드와 같은 스타일 유지
  - 분면 중 하나를 확률/후보로 색칠하지 않음
  - 분면 내부 Hz 표시와 점수바 제거
  - 첫 메뉴 라벨은 명령문 / 의문문 / 직접입력 / 기능키로 통일
  - 창은 가능한 한 가로폭을 넓게 사용

  python ssvep_online.py
  python ssvep_online.py --demo
  실행 후 콘솔에서 실험자 ID와 EEG 포트를 입력합니다. 포트는 Enter 입력 시 COM3를 사용합니다.

[저장 파일]
  recordings/sub{ID}/online/runXX/sub{ID}_runXX_{YYYYMMDD}_{HHMM}.csv
  recordings/sub{ID}/online/runXX/sub{ID}_runXX_{YYYYMMDD}_{HHMM}_events.csv
  recordings/sub{ID}/online/runXX/ai_001.py, ai_002.py, ...

[조작]
  Esc       : 종료

[SSVEP 파라미터]
  주파수: 9.25, 10, 12, 15 Hz
  분석 윈도우: 3.8초
  신뢰도 임계값: 0.27
  raw score 1등/2등 비율 임계값: 2.5x
  연속 일치: 4회
"""

import argparse
import csv
import math
import os
import queue
import threading
import time
from collections import deque
from datetime import datetime

import numpy as np
import pygame
from scipy.signal import butter, filtfilt

from ai_coder import AICoder
from eeg_collector import EEGCollector
from ssvep_fbcca import FBCCA, StandardCCA


FALLBACK_SCREEN_W = 1500
FALLBACK_SCREEN_H = 840
WINDOW_POS_X = 0
WINDOW_POS_Y = 0
FRAME_RATE = 60

BG_COLOR = (30, 30, 30)
DIM_RECT = (60, 60, 60)
BRIGHT_RECT = (180, 180, 180)
DIM_TEXT = (50, 50, 50)
BRIGHT_TEXT = (200, 200, 200)
LINE_COLOR = (50, 50, 50)
WHITE = (240, 240, 240)
TARGET_COLOR = (255, 180, 80)
GREEN = (80, 200, 80)
CYAN = (80, 200, 200)
GRAY = (120, 120, 120)

FREQS = [9.25, 10.0, 12.0, 15.0]
FS = 222
SSVEP_WINDOW_SEC = 3.8
SSVEP_SHIFT_SEC = 1.0
SSVEP_CONF_THRESHOLD = 0.30          # softmax 신뢰도 임계값 (실측 EEG 30%대 분포 기준)
SSVEP_SCORE_RATIO_THRESHOLD = 2.5    # raw score 1등/2등 비율 임계값 (false positive 방지)
SSVEP_CONSEC_REQUIRED = 4            # 연속 일치 횟수 (10회 이상 안정적이라 여유롭게 4회)
SSVEP_TIMEOUT_SEC = 30.0
AI_REVIEW_SEC = 30.0
INTER_SELECTION_REST_SEC = 3.0
PREPARE_DURATION_SEC = 5.0
TIMEOUT_REST_SEC = 3.0
DEFAULT_EEG_PORT = "COM3"


def get_window_size():
    info = pygame.display.Info()
    width = info.current_w if info.current_w > 0 else FALLBACK_SCREEN_W
    height = info.current_h - 140 if info.current_h > 0 else FALLBACK_SCREEN_H
    height = max(700, min(FALLBACK_SCREEN_H, height))
    return width, height


# ============================================================
# 전처리 필터 — FBCCA 들어가기 전 raw 신호 정제
# ============================================================
def bandpass(data, low=1.0, high=40.0, fs=FS, order=4):
    """광역 대역통과 — DC drift, 근전도, 고주파 잡음 제거"""
    b, a = butter(order, [low, high], btype="band", fs=fs)
    return filtfilt(b, a, data)


def notch(data, freq=60.0, fs=FS, order=2):
    """노치 — 60Hz 전원 노이즈 제거"""
    b, a = butter(order, [freq - 2.0, freq + 2.0], btype="bandstop", fs=fs)
    return filtfilt(b, a, data)


class RingBuffer:
    def __init__(self, max_samples, n_ch=1):
        self.buffer = deque(maxlen=max_samples)
        self.n_ch = n_ch
        self.lock = threading.Lock()

    def push(self, sample):
        with self.lock:
            self.buffer.append(sample)

    def get_recent(self, n_samples):
        with self.lock:
            data = list(self.buffer)
        if len(data) < n_samples:
            arr = np.array([0.0] * (n_samples - len(data)) + data, dtype=np.float32)
        else:
            arr = np.array(data[-n_samples:], dtype=np.float32)
        return arr.reshape(self.n_ch, -1)

    def __len__(self):
        return len(self.buffer)


class SSVEPAnalyzer(threading.Thread):
    def __init__(self, ring_buffer, result_queue):
        super().__init__(daemon=True)
        self.ring = ring_buffer
        self.queue = result_queue
        self.clf = FBCCA(freqs=FREQS, fs=FS)
        self.cca_clf = StandardCCA(freqs=FREQS, fs=FS)
        self.window_samples = int(FS * SSVEP_WINDOW_SEC)
        self._active = threading.Event()
        self._stop_event = threading.Event()
        self._last_quad = -1
        self._consec = 0
        self._start_t = 0.0

    def activate(self):
        self._last_quad = -1
        self._consec = 0
        self._start_t = time.time()
        self._active.set()

    def deactivate(self):
        self._active.clear()

    def stop(self):
        self._stop_event.set()
        self._active.clear()

    def run(self):
        while not self._stop_event.is_set():
            if not self._active.is_set():
                time.sleep(0.1)
                continue
            if len(self.ring) < self.window_samples:
                time.sleep(0.1)
                continue

            window = self.ring.get_recent(self.window_samples)
            try:
                # 전처리: bandpass(1~40Hz) + notch(60Hz) — 잡음 제거 후 분류
                sig = window[0]
                sig = bandpass(sig, low=1.0, high=40.0, fs=FS)
                sig = notch(sig, freq=60.0, fs=FS)
                window = sig.reshape(1, -1).astype(np.float32)

                # FBCCA raw score 직접 계산 (softmax 압축 전 원본 점수 — 비율 검증용)
                scores = self.clf._compute_scores(window)
                exp_s = np.exp(scores - np.max(scores))
                probs = exp_s / exp_s.sum()

                # Standard CCA는 선택에 사용하지 않고 사후 비교 로그용으로만 계산
                cca_scores = self.cca_clf._compute_scores(window)
                cca_exp_s = np.exp(cca_scores - np.max(cca_scores))
                cca_probs = cca_exp_s / cca_exp_s.sum()
            except Exception as e:
                print(f"[FBCCA 오류] {e}")
                time.sleep(0.5)
                continue

            quad = int(np.argmax(scores))
            conf = float(probs[quad])

            # raw score 1등 vs 2등 비율 (softmax 압축 전이라 차이가 또렷)
            sorted_scores = np.sort(scores)[::-1]
            score_top1 = float(sorted_scores[0])
            score_top2 = float(sorted_scores[1])
            score_ratio = score_top1 / max(score_top2, 1e-10)

            cca_quad = int(np.argmax(cca_scores))
            cca_conf = float(cca_probs[cca_quad])
            cca_sorted_scores = np.sort(cca_scores)[::-1]
            cca_score_top1 = float(cca_sorted_scores[0])
            cca_score_top2 = float(cca_sorted_scores[1])
            cca_score_ratio = cca_score_top1 / max(cca_score_top2, 1e-10)

            if quad == self._last_quad:
                self._consec += 1
            else:
                self._consec = 1
                self._last_quad = quad

            self.queue.put({
                "type": "ssvep_update",
                "quad": quad,
                "conf": conf,
                "consec": self._consec,
                "probs": probs.tolist(),
                "score_ratio": score_ratio,
                "scores": scores.tolist(),
                "cca_quad": cca_quad,
                "cca_conf": cca_conf,
                "cca_score_ratio": cca_score_ratio,
                "cca_scores": cca_scores.tolist(),
                "cca_probs": cca_probs.tolist(),
            })

            # 확정 조건 — 세 조건 모두 만족해야 함
            #   ① softmax 신뢰도 ≥ SSVEP_CONF_THRESHOLD
            #   ② raw score 비율(1등/2등) ≥ SSVEP_SCORE_RATIO_THRESHOLD
            #   ③ 연속 일치 횟수 ≥ SSVEP_CONSEC_REQUIRED
            if (conf >= SSVEP_CONF_THRESHOLD
                    and score_ratio >= SSVEP_SCORE_RATIO_THRESHOLD
                    and self._consec >= SSVEP_CONSEC_REQUIRED):
                self.queue.put({
                    "type": "ssvep_confirmed",
                    "quad": quad,
                    "conf": conf,
                    "consec": self._consec,
                    "score_ratio": score_ratio,
                    "scores": scores.tolist(),
                    "probs": probs.tolist(),
                    "cca_quad": cca_quad,
                    "cca_conf": cca_conf,
                    "cca_score_ratio": cca_score_ratio,
                    "cca_scores": cca_scores.tolist(),
                    "cca_probs": cca_probs.tolist(),
                })
                self.deactivate()
                continue

            if time.time() - self._start_t > SSVEP_TIMEOUT_SEC:
                self.queue.put({"type": "ssvep_timeout"})
                self.deactivate()
                continue

            time.sleep(SSVEP_SHIFT_SEC)


def _letter_leaf(a, b, c, return_path=None):
    return {
        "options": [a, b, c, "뒤로"],
        "descriptions": ["", "", "", "전 화면으로"],
        "kind": "leaf_letter",
        "return_path": return_path or [],
    }


def _phrase_leaf(a, b, c):
    return {
        "options": [a, b, c, "뒤로"],
        "descriptions": ["", "", "", "전 화면으로"],
        "kind": "leaf_phrase",
    }


_MENU_TREE = {
    "options": ["명령문", "의문문", "직접입력", "기능키"],
    "descriptions": ["Make / Print / Search", "How to / What is / Why", "숫자 / 알파벳", "스페이스 / 지우기 / 실행"],
    "kind": "submenu",
    "children": [
        _phrase_leaf("Make", "Print", "Search"),
        _phrase_leaf("How to", "What is", "Why"),
        {
            "options": ["숫자,괄호", "알파벳,/", "~", "뒤로"],
            "descriptions": ["", "", "", "전 화면으로"],
            "kind": "direct_input",
            "children": [
                {
                    "options": ["0~2", "3~5", "6~8", "9/뒤로"],
                    "descriptions": ["0 1 2", "3 4 5", "6 7 8", "9 ( )"],
                    "kind": "submenu",
                    "children": [
                        _letter_leaf("0", "1", "2", return_path=[2]),
                        _letter_leaf("3", "4", "5", return_path=[2]),
                        _letter_leaf("6", "7", "8", return_path=[2]),
                        _letter_leaf("9", "(", ")", return_path=[2]),
                    ],
                },
                {
                    "options": ["A~I", "J~R", "S~Z", "뒤로"],
                    "descriptions": [
                        "A B C / D E F / G H I",
                        "J K L / M N O / P Q R",
                        "S T U / V W X / Y Z /",
                        "전 화면으로",
                    ],
                    "kind": "submenu",
                    "children": [
                        {
                            "options": ["A~C", "D~F", "G~I", "뒤로"],
                            "descriptions": ["A B C", "D E F", "G H I", "전 화면으로"],
                            "kind": "submenu",
                            "children": [
                                _letter_leaf("A", "B", "C", return_path=[2]),
                                _letter_leaf("D", "E", "F", return_path=[2]),
                                _letter_leaf("G", "H", "I", return_path=[2]),
                                None,
                            ],
                        },
                        {
                            "options": ["J~L", "M~O", "P~R", "뒤로"],
                            "descriptions": ["J K L", "M N O", "P Q R", "전 화면으로"],
                            "kind": "submenu",
                            "children": [
                                _letter_leaf("J", "K", "L", return_path=[2]),
                                _letter_leaf("M", "N", "O", return_path=[2]),
                                _letter_leaf("P", "Q", "R", return_path=[2]),
                                None,
                            ],
                        },
                        {
                            "options": ["S~U", "V~X", "Y/Z", "뒤로"],
                            "descriptions": ["S T U", "V W X", "Y Z /", "전 화면으로"],
                            "kind": "submenu",
                            "children": [
                                _letter_leaf("S", "T", "U", return_path=[2]),
                                _letter_leaf("V", "W", "X", return_path=[2]),
                                _letter_leaf("Y", "Z", "/", return_path=[2]),
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
        {
            "options": ["스페이스", "지우기", "실행", "뒤로"],
            "descriptions": ["", "", "", "전 화면으로"],
            "kind": "leaf_function",
        },
    ],
}


class MenuState:
    def __init__(self):
        self.path = []
        self.output = ""

    def _get_node(self):
        node = _MENU_TREE
        for idx in self.path:
            node = node["children"][idx]
        return node

    @property
    def current_labels(self):
        return self._get_node()["options"]

    @property
    def current_descriptions(self):
        node = self._get_node()
        return node.get("descriptions", [""] * len(node["options"]))

    @property
    def path_str(self):
        if not self.path:
            return "메뉴 루트"
        labels = []
        node = _MENU_TREE
        for idx in self.path:
            labels.append(node["options"][idx])
            node = node["children"][idx]
        return " → ".join(labels)

    def select(self, idx):
        node = self._get_node()
        label = node["options"][idx]

        if label == "뒤로":
            if self.path:
                self.path.pop()
            return "back"

        kind = node.get("kind", "submenu")
        if kind == "direct_input":
            if label == "~":
                self.output += "~"
                self.path = [2]
                return "char"

        if kind == "leaf_function":
            if label == "스페이스":
                self.output += " "
                self.path = []
                return "space"
            if label == "지우기":
                self.output = self.output[:-1]
                self.path = []
                return "delete"
            if label == "실행":
                self.path = []
                return "run"

        if kind == "leaf_phrase":
            self.output += label + " "
            self.path = []
            return "phrase"

        if kind == "leaf_letter":
            self.output += label
            self.path = list(node.get("return_path", []))
            return "char"

        self.path.append(idx)
        return "navigate"

class OnlineExperiment:
    @staticmethod
    def _next_run_name(base_dir):
        os.makedirs(base_dir, exist_ok=True)
        max_idx = 0
        for name in os.listdir(base_dir):
            if not name.startswith("run"):
                continue
            suffix = name[3:]
            if suffix.isdigit():
                max_idx = max(max_idx, int(suffix))
        return f"run{max_idx + 1:02d}"

    def __init__(self, subject, port="COM3", demo_mode=False):
        os.environ["SDL_VIDEO_WINDOW_POS"] = f"{WINDOW_POS_X},{WINDOW_POS_Y}"
        pygame.init()
        self.screen_w, self.screen_h = get_window_size()
        self.screen = pygame.display.set_mode((self.screen_w, self.screen_h))
        pygame.display.set_caption(f"BCI Coding - sub{subject} [FBCCA]")
        self.clock = pygame.time.Clock()

        self.font_item = pygame.font.SysFont("malgun gothic", 80, bold=True)
        self.font_desc = pygame.font.SysFont("malgun gothic", 24)
        self.font_med = pygame.font.SysFont("malgun gothic", 28, bold=True)
        self.font_sml = pygame.font.SysFont("malgun gothic", 20)
        self.font_tiny = pygame.font.SysFont("malgun gothic", 16)
        self.font_status = pygame.font.SysFont("malgun gothic", 30, bold=True)
        self.font_target_title = pygame.font.SysFont("malgun gothic", 50, bold=True)
        self.font_ai_title = pygame.font.SysFont("malgun gothic", 56, bold=True)
        self.font_ai_text = pygame.font.SysFont("malgun gothic", 30, bold=True)
        self.font_ai_code = pygame.font.Font("C:/Windows/Fonts/malgun.ttf", 20)

        self.top_bar_h = 60
        self.bottom_bar_h = 30
        self.grid_top = self.top_bar_h
        self.grid_bottom = self.screen_h - self.bottom_bar_h
        self.grid_h = self.grid_bottom - self.grid_top
        self.grid_left = 0
        self.grid_right = self.screen_w
        self.grid_w = self.grid_right - self.grid_left

        self.centers = [
            (self.screen_w // 4, self.grid_top + self.grid_h // 4),
            (self.screen_w * 3 // 4, self.grid_top + self.grid_h // 4),
            (self.screen_w // 4, self.grid_top + self.grid_h * 3 // 4),
            (self.screen_w * 3 // 4, self.grid_top + self.grid_h * 3 // 4),
        ]
        self.cell_w = self.screen_w // 2 - 30
        self.cell_h = self.grid_h // 2 - 30

        self.subject = subject
        self.demo_mode = demo_mode

        self.ring = RingBuffer(max_samples=int(FS * 10), n_ch=1)
        self.result_queue = queue.Queue()
        self.analyzer = SSVEPAnalyzer(self.ring, self.result_queue)
        self.analyzer.start()

        # 파일 경로 (실행 1회 = runXX 폴더 1개)
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        base_online_dir = os.path.join("recordings", f"sub{subject}", "online")
        self.run_name = self._next_run_name(base_online_dir)
        self.run_dir = os.path.join(base_online_dir, self.run_name)
        os.makedirs(self.run_dir, exist_ok=True)
        base_name = f"sub{subject}_{self.run_name}_{ts}"
        self.eeg_path = os.path.join(self.run_dir, f"{base_name}.csv")
        self.log_path = os.path.join(self.run_dir, f"{base_name}_events.csv")
        self.ai_code_count = 0

        # EEG 수집기 — raw EEG CSV 저장과 ring buffer 스트리밍 동시 수행
        self.eeg = EEGCollector(port=port)
        self.eeg_recording_started = False
        if not demo_mode:
            if self.eeg.connect():
                # filename + on_sample → CSV 저장과 실시간 ring buffer push를 동시에 수행
                self.eeg.start_recording(filename=self.eeg_path, on_sample=self.ring.push)
                self.eeg_recording_started = True
                print(f"[EEG] 저장 + 실시간 스트리밍 시작: {self.eeg_path}")
            else:
                print("[경고] EEG 연결 실패 — 자극 화면만 진행")

        self.menu = MenuState()
        self.ai = AICoder()
        self.ai_result = None
        self.ai_options = []
        self.ai_code_files = []
        self.ai_option_intents = []
        self.ai_choice_labels = ["1번 코드", "2번 코드", "더 입력하기", "코드 다시 보기"]
        self.ai_review_start = 0.0
        self.ai_selected_code = ""
        self.ai_selected_file = ""
        self.ai_selected_intent = ""
        self.ai_loading = False
        self.ai_input_text = ""
        self.ai_refined_text = ""

        self.phase = "ssvep"
        self.ssvep_conf = 0.0
        self.ssvep_quad = -1
        self.ssvep_consec = 0
        self.ssvep_probs = [0.25] * 4
        self.ssvep_score_ratio = 1.0
        self.feedback_text = ""
        self.feedback_timer = 0.0
        self.timeout_return_ai_choice = False

        self.log_file = open(self.log_path, "w", newline="", encoding="utf-8")
        self.log_writer = csv.writer(self.log_file)
        self.log_writer.writerow(["timestamp", "event", "data"])

        self._start_preparing()
        print("=" * 55)
        print(f"온라인 모드 시작 - sub{subject}")
        print(f"Demo: {demo_mode} | Threshold: {SSVEP_CONF_THRESHOLD} | Consecutive: {SSVEP_CONSEC_REQUIRED}")
        print("[조작] Esc=종료")
        print("=" * 55)

    def log(self, event, data=""):
        ts = datetime.now().strftime("%Y %m %d %H:%M:%S.%f")
        self.log_writer.writerow([ts, event, data])
        self.log_file.flush()

    def _start_preparing(self):
        self.phase = "preparing"
        self.prepare_start = time.time()
        self.log("PHASE_PREPARING")

    def _start_ssvep(self):
        self.phase = "ssvep"
        self.ssvep_conf = 0.0
        self.ssvep_quad = -1
        self.ssvep_consec = 0
        self.ssvep_probs = [0.25] * 4
        self.ssvep_score_ratio = 1.0
        self.analyzer.activate()
        self.log("PHASE_SSVEP")

    def _finish_selection(self, quad):
        # select() 호출 전에 현재 노드의 라벨을 미리 캡처 (navigate 시 path가 바뀌므로)
        pre_labels = list(self.menu.current_labels)
        chosen_label = pre_labels[quad]

        result = self.menu.select(quad)
        self.log("SELECTION", f"quad={quad}, result={result}, output={self.menu.output!r}")

        if result == "run":
            self._trigger_ai()
            return

        # 글자/문구/공백이 출력 문자열에 누적되는 경우 = "입력"
        if result == "char":
            self.feedback_text = f"입력: '{chosen_label}'"
        elif result == "phrase":
            self.feedback_text = f"입력: {chosen_label}"
        elif result == "space":
            self.feedback_text = "입력: 스페이스"
        elif result == "delete":
            self.feedback_text = "지우기"
        else:
            # navigate(서브메뉴 진입), back(뒤로) 등 메뉴 탐색은 "선택"
            self.feedback_text = f"선택: {chosen_label}"

        self.feedback_timer = time.time()
        self.phase = "feedback"

    def _refine_intent(self, text):
        return (
            "Python으로 다음 입력을 해석한 코드 후보 2개를 작성해줘.\n"
            "두 후보는 코드 구조만 다르게 만들지 말고, 입력 문장에 대한 해석/보정 문장 자체가 서로 달라야 해.\n"
            "1번과 2번의 '# 의도:' 문장은 반드시 서로 달라야 해.\n"
            "1번은 입력을 가장 단순하고 직접적인 의미로 해석한 코드로 작성해줘.\n"
            "2번은 입력을 다르게 해석할 수 있는 합리적인 대안 의도로 작성해줘.\n"
            "두 후보는 모두 기본적으로 콘솔에서 실행 가능한 Python 코드로 작성해줘.\n"
            "명령에 GUI, 웹, 파일 저장이 명시되지 않았다면 GUI, 웹 서버, 파일 입출력은 사용하지 마.\n"
            "단순히 print를 함수로 감싸거나, def/main/while만 추가하거나, 변수명만 다른 중복 후보는 만들지 마.\n"
            "반드시 아래 형식으로만 출력해줘.\n"
            "### CODE 1\n"
            "# 의도: [첫 번째 보정 문장]\n"
            "[첫 번째 Python 코드]\n"
            "### CODE 2\n"
            "# 의도: [두 번째 보정 문장]\n"
            "[두 번째 Python 코드]\n"
            f"입력: {text}"
        )

    def _trigger_ai(self):
        self.phase = "ai"
        self.ai_loading = True
        self.ai_result = None
        self.ai_options = []
        self.ai_code_files = []
        self.ai_option_intents = []
        self.ai_review_start = 0.0
        self.ai_selected_code = ""
        self.ai_selected_file = ""
        self.ai_selected_intent = ""
        text = self.menu.output.strip() or "Hello World 출력"
        self.ai_input_text = text
        self.ai_refined_text = self._refine_intent(text)
        self.ai.generate(self.ai_refined_text)
        self.log("AI_REQUEST", f"raw={text!r}, refined={self.ai_refined_text!r}")

    def _split_ai_options(self, code):
        marker1 = "### CODE 1"
        marker2 = "### CODE 2"
        if marker1 in code and marker2 in code:
            part1 = code.split(marker1, 1)[1].split(marker2, 1)[0].strip()
            part2 = code.split(marker2, 1)[1].strip()
            return [part1, part2]
        return [code.strip(), code.strip()]

    def _extract_ai_intent(self, code):
        for line in code.splitlines():
            stripped = line.strip()
            if stripped.startswith("# 의도:"):
                return stripped.split(":", 1)[1].strip()
        return self.ai_input_text

    def _save_ai_code(self, code):
        self.ai_code_count += 1
        filename = f"ai_{self.ai_code_count:03d}.py"
        path = os.path.join(self.run_dir, filename)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(code.rstrip())
            f.write("\n")
        return filename

    def _continue_after_ai(self):
        self.menu.output = ""
        self.menu.path = []
        self.log("AI_CONTINUE_CLEAR_INPUT")
        self._start_ssvep()

    def _start_ai_choice(self):
        self.phase = "ai_choice"
        self.ssvep_conf = 0.0
        self.ssvep_quad = -1
        self.ssvep_consec = 0
        self.ssvep_probs = [0.25] * 4
        self.ssvep_score_ratio = 1.0
        self.analyzer.activate()
        self.log("PHASE_AI_CHOICE")

    def _handle_ai_choice(self, quad):
        label = self.ai_choice_labels[quad]
        self.log("AI_CHOICE", f"quad={quad}, label={label!r}, files={self.ai_code_files!r}")
        if quad == 0:
            file_name = self.ai_code_files[0] if self.ai_code_files else "1번 코드"
            self.ai_selected_code = self.ai_options[0] if self.ai_options else self.ai_result
            self.ai_selected_file = file_name
            self.ai_selected_intent = self.ai_option_intents[0] if self.ai_option_intents else self.ai_input_text
            self.menu.output = ""
            self.menu.path = []
            self.log("AI_CODE_SELECTED", f"option=1, file={file_name!r}")
            self.phase = "ai_selected"
            return
        if quad == 1:
            file_name = self.ai_code_files[1] if len(self.ai_code_files) > 1 else "2번 코드"
            self.ai_selected_code = self.ai_options[1] if len(self.ai_options) > 1 else self.ai_result
            self.ai_selected_file = file_name
            self.ai_selected_intent = self.ai_option_intents[1] if len(self.ai_option_intents) > 1 else self.ai_input_text
            self.menu.output = ""
            self.menu.path = []
            self.log("AI_CODE_SELECTED", f"option=2, file={file_name!r}")
            self.phase = "ai_selected"
            return
        if quad == 2:
            self.menu.path = [2]
            self.log("AI_CONTINUE_MORE_INPUT", f"output={self.menu.output!r}")
            self._start_ssvep()
            return
        if quad == 3:
            self.phase = "ai"
            self.ai_review_start = time.time()
            return

    def draw_grid_lines(self):
        pygame.draw.line(
            self.screen, LINE_COLOR,
            (self.screen_w // 2, self.grid_top),
            (self.screen_w // 2, self.grid_bottom), 3,
        )
        pygame.draw.line(
            self.screen, LINE_COLOR,
            (self.grid_left, (self.grid_top + self.grid_bottom) // 2),
            (self.grid_right, (self.grid_top + self.grid_bottom) // 2), 3,
        )

    def _draw_quadrant(self, idx, ssvep_on=None):
        cx, cy = self.centers[idx]
        rect = pygame.Rect(
            cx - self.cell_w // 2, cy - self.cell_h // 2,
            self.cell_w, self.cell_h,
        )
        if ssvep_on is True:
            bg, fg = BRIGHT_RECT, DIM_TEXT
        elif ssvep_on is False:
            bg, fg = DIM_RECT, BRIGHT_TEXT
        else:
            bg, fg = DIM_RECT, BRIGHT_TEXT

        pygame.draw.rect(self.screen, bg, rect, border_radius=14)
        if self.phase == "ai_choice":
            label = self.ai_choice_labels[idx]
            desc = ""
        else:
            label = self.menu.current_labels[idx]
            desc = self.menu.current_descriptions[idx]
        label_y = cy - 38 if desc else cy
        surf = self.font_item.render(label, True, fg)
        self.screen.blit(surf, surf.get_rect(center=(cx, label_y)))

        if desc:
            lines = desc.split("\n")
            line_gap = 4
            total_h = len(lines) * self.font_desc.get_height() + (len(lines) - 1) * line_gap
            y = cy + 34 - total_h // 2
            for line in lines:
                desc_surf = self.font_desc.render(line, True, fg)
                self.screen.blit(desc_surf, desc_surf.get_rect(center=(cx, y + desc_surf.get_height() // 2)))
                y += desc_surf.get_height() + line_gap

    def _draw_all(self, ssvep_states=None):
        self.screen.fill(BG_COLOR)
        self.draw_grid_lines()
        for i in range(4):
            ssvep_on = ssvep_states[i] if ssvep_states is not None else None
            self._draw_quadrant(i, ssvep_on=ssvep_on)

    def _draw_top_bar(self):
        out = self.menu.output.replace("\n", " [ENTER] ")[-80:]
        surf = self.font_med.render(f"입력: {out}|", True, WHITE)
        self.screen.blit(surf, (20, 15))

    def _draw_bottom_bar(self):
        # softmax/비율/연속/후보 표시는 터미널로 옮김 (분면 공간 확보)
        hint = self.font_tiny.render("Esc=종료", True, GRAY)
        self.screen.blit(
            hint,
            (self.screen_w - hint.get_width() - 20, self.grid_bottom + 12),
        )

    def _draw_ai(self):
        self.screen.fill(BG_COLOR)
        cx, cy = self.screen_w // 2, self.screen_h // 2
        content_w = min(self.screen_w - 220, 1280)
        content_x = self.screen_w // 2 - content_w // 2

        def draw_wrapped(text, font, color, x, y, max_w, line_h):
            words = text.split(" ")
            lines = []
            current = ""
            for word in words:
                candidate = word if not current else f"{current} {word}"
                if font.size(candidate)[0] <= max_w:
                    current = candidate
                else:
                    if current:
                        lines.append(current)
                    current = word
            if current:
                lines.append(current)

            for line in lines:
                surf = font.render(line, True, color)
                self.screen.blit(surf, (x, y))
                y += line_h
            return y

        if self.ai_loading:
            title = self.font_ai_title.render("AI 코드 생성 중...", True, CYAN)
            self.screen.blit(title, title.get_rect(center=(cx, cy - 100)))
            y = cy - 18
            raw = self.font_ai_text.render(f"입력 문장: {self.ai_input_text}", True, WHITE)
            self.screen.blit(raw, (content_x, y))
            y += 48
            draw_wrapped(
                "코드 후보 2개를 생성하는 중입니다.",
                self.font_ai_text,
                TARGET_COLOR,
                content_x,
                y,
                content_w,
                38,
            )
        elif self.ai_result:
            title = self.font_ai_title.render("AI 코드 생성 완료", True, CYAN)
            y = cy - 330

            self.screen.blit(title, title.get_rect(center=(cx, y)))
            y += 78

            raw = self.font_ai_text.render(f"입력 문장: {self.ai_input_text}", True, WHITE)
            self.screen.blit(raw, (content_x, y))
            y += 48

            intents = self.ai_option_intents or [self.ai_input_text, self.ai_input_text]
            y = draw_wrapped(f"1번 코드 [{intents[0]}]", self.font_ai_text, TARGET_COLOR, content_x, y, content_w, 38)
            if len(intents) > 1:
                y = draw_wrapped(f"2번 코드 [{intents[1]}]", self.font_ai_text, TARGET_COLOR, content_x, y, content_w, 38)
            y += 36

            box_gap = 24
            box_y = y
            box_w = (content_w - box_gap) // 2
            box_h = max(260, self.screen_h - box_y - 92)
            options = self.ai_options or [self.ai_result, ""]

            def draw_code_box(option_idx, code):
                box_x = content_x + option_idx * (box_w + box_gap)
                code_lines = code.split("\n")
                pygame.draw.rect(self.screen, (24, 24, 24), (box_x, box_y, box_w, box_h), border_radius=8)
                pygame.draw.rect(self.screen, (95, 95, 95), (box_x, box_y, box_w, box_h), width=2, border_radius=8)

                header = self.font_med.render(f"{option_idx + 1}번 코드", True, WHITE)
                self.screen.blit(header, (box_x + 24, box_y + 18))
                pygame.draw.line(
                    self.screen,
                    (75, 75, 75),
                    (box_x + 20, box_y + 58),
                    (box_x + box_w - 20, box_y + 58),
                    1,
                )

                code_y = box_y + 76
                code_x = box_x + 24
                code_max_w = box_w - 48
                code_bottom = box_y + box_h - 24
                code_clip = pygame.Rect(code_x, code_y, code_max_w, max(0, code_bottom - code_y))
                old_clip = self.screen.get_clip()
                self.screen.set_clip(code_clip)
                for line in code_lines:
                    if code_y + line_h > code_bottom:
                        more = self.font_ai_code.render("...", True, BRIGHT_TEXT)
                        self.screen.blit(more, (code_x, max(code_y, code_bottom - line_h)))
                        break
                    s = self.font_ai_code.render(line, True, BRIGHT_TEXT)
                    self.screen.blit(s, (code_x, code_y))
                    code_y += line_h
                self.screen.set_clip(old_clip)

            line_h = 27
            draw_code_box(0, options[0])
            draw_code_box(1, options[1] if len(options) > 1 else "")

            remaining = max(0, int(AI_REVIEW_SEC - (time.time() - self.ai_review_start)) + 1)
            hint = self.font_med.render(f"{remaining}초 후 코드 선택 화면", True, GRAY)
            self.screen.blit(hint, hint.get_rect(center=(self.screen_w // 2, self.screen_h - 30)))

    def _draw_ai_selected(self):
        self.screen.fill(BG_COLOR)
        cx, cy = self.screen_w // 2, self.screen_h // 2
        content_w = min(self.screen_w - 220, 1280)
        content_x = self.screen_w // 2 - content_w // 2

        def draw_wrapped(text, font, color, x, y, max_w, line_h):
            words = text.split(" ")
            lines = []
            current = ""
            for word in words:
                candidate = word if not current else f"{current} {word}"
                if font.size(candidate)[0] <= max_w:
                    current = candidate
                else:
                    if current:
                        lines.append(current)
                    current = word
            if current:
                lines.append(current)

            for line in lines:
                surf = font.render(line, True, color)
                self.screen.blit(surf, (x, y))
                y += line_h
            return y

        title = self.font_ai_title.render("선택된 코드", True, CYAN)
        y = cy - 340
        self.screen.blit(title, title.get_rect(center=(cx, y)))
        y += 76

        raw = self.font_ai_text.render(f"입력 문장: {self.ai_input_text}", True, WHITE)
        self.screen.blit(raw, (content_x, y))
        y += 46

        y = draw_wrapped(
            f"선택 코드 [{self.ai_selected_intent or self.ai_input_text}]",
            self.font_ai_text,
            TARGET_COLOR,
            content_x,
            y,
            content_w,
            36,
        )
        y += 20

        file_surf = self.font_ai_text.render(f"저장 파일: {self.ai_selected_file}", True, WHITE)
        self.screen.blit(file_surf, (content_x, y))
        y += 54

        box_x = content_x
        box_y = y
        box_w = content_w
        box_h = min(self.screen_h - box_y - 92, 520)
        pygame.draw.rect(self.screen, (24, 24, 24), (box_x, box_y, box_w, box_h), border_radius=8)
        pygame.draw.rect(self.screen, (95, 95, 95), (box_x, box_y, box_w, box_h), width=2, border_radius=8)

        header = self.font_med.render("생성된 코드", True, WHITE)
        self.screen.blit(header, (box_x + 28, box_y + 20))
        pygame.draw.line(
            self.screen,
            (75, 75, 75),
            (box_x + 24, box_y + 62),
            (box_x + box_w - 24, box_y + 62),
            1,
        )

        line_h = 27
        code_y = box_y + 80
        code_x = box_x + 28
        code_max_w = box_w - 56
        code_bottom = box_y + box_h - 24
        code_clip = pygame.Rect(code_x, code_y, code_max_w, max(0, code_bottom - code_y))
        old_clip = self.screen.get_clip()
        self.screen.set_clip(code_clip)
        for line in self.ai_selected_code.split("\n"):
            if code_y + line_h > code_bottom:
                more = self.font_ai_code.render("...", True, BRIGHT_TEXT)
                self.screen.blit(more, (code_x, max(code_y, code_bottom - line_h)))
                break
            s = self.font_ai_code.render(line, True, BRIGHT_TEXT)
            self.screen.blit(s, (code_x, code_y))
            code_y += line_h
        self.screen.set_clip(old_clip)

        hint = self.font_med.render("Esc=종료", True, GRAY)
        self.screen.blit(hint, hint.get_rect(center=(self.screen_w // 2, self.screen_h - 30)))

    def run(self):
        frame = 0
        while True:
            self.clock.tick(FRAME_RATE)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.cleanup()
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.cleanup()
                        return

            while not self.result_queue.empty():
                msg = self.result_queue.get_nowait()
                if msg["type"] == "ssvep_update":
                    self.ssvep_quad = msg["quad"]
                    self.ssvep_conf = msg["conf"]
                    self.ssvep_consec = msg["consec"]
                    self.ssvep_probs = msg["probs"]
                    self.ssvep_score_ratio = msg.get("score_ratio", 1.0)
                    # 터미널 실시간 출력 (EEG 수집 중 줄 바로 아래에 갱신)
                    # \n 으로 다음 줄로 가서 SSVEP 정보 쓰고, \033[F 로 다시 위로 올라옴
                    # → EEG 줄은 위에서 \r 로 갱신, SSVEP 줄은 아래에서 갱신, 두 줄 동시 표시
                    if self.phase == "ssvep":
                        _cand = (self.menu.current_labels[msg["quad"]]
                                 if 0 <= msg["quad"] < 4 else "?")
                    elif self.phase == "ai_choice":
                        _cand = (self.ai_choice_labels[msg["quad"]]
                                 if 0 <= msg["quad"] < 4 else "?")
                    else:
                        _cand = "?"
                    print(f"\n[SSVEP] softmax {msg['conf']*100:5.1f}%  "
                          f"비율 {msg.get('score_ratio', 0):5.2f}x  "
                          f"연속 {msg['consec']}회  후보: {_cand}        \033[F",
                          end='', flush=True)
                    self.log(
                        "SSVEP_UPDATE",
                        f"fbcca_quad={msg['quad']}, "
                        f"fbcca_conf={msg['conf']:.4f}, "
                        f"fbcca_ratio={msg.get('score_ratio', 0.0):.4f}, "
                        f"fbcca_consec={msg['consec']}, "
                        f"fbcca_scores={msg.get('scores', [])}, "
                        f"fbcca_probs={msg.get('probs', [])}, "
                        f"cca_quad={msg.get('cca_quad', -1)}, "
                        f"cca_conf={msg.get('cca_conf', 0.0):.4f}, "
                        f"cca_ratio={msg.get('cca_score_ratio', 0.0):.4f}, "
                        f"cca_scores={msg.get('cca_scores', [])}, "
                        f"cca_probs={msg.get('cca_probs', [])}",
                    )
                elif msg["type"] == "ssvep_confirmed":
                    quad = msg["quad"]
                    self.log(
                        "SSVEP_CONFIRMED",
                        f"fbcca_quad={quad}, "
                        f"fbcca_conf={msg['conf']:.4f}, "
                        f"fbcca_ratio={msg.get('score_ratio', 0.0):.4f}, "
                        f"fbcca_consec={msg.get('consec', 0)}, "
                        f"fbcca_scores={msg.get('scores', [])}, "
                        f"fbcca_probs={msg.get('probs', [])}, "
                        f"cca_quad={msg.get('cca_quad', -1)}, "
                        f"cca_conf={msg.get('cca_conf', 0.0):.4f}, "
                        f"cca_ratio={msg.get('cca_score_ratio', 0.0):.4f}, "
                        f"cca_scores={msg.get('cca_scores', [])}, "
                        f"cca_probs={msg.get('cca_probs', [])}",
                    )
                    if self.phase == "ai_choice":
                        self._handle_ai_choice(quad)
                    else:
                        self._finish_selection(quad)
                elif msg["type"] == "ssvep_timeout":
                    self.timeout_return_ai_choice = (self.phase == "ai_choice")
                    self.timeout_start = time.time()
                    self.phase = "timeout"
                    self.log("PHASE_TIMEOUT")

            if self.phase == "ai" and self.ai_loading:
                result = self.ai.get_result()
                if result:
                    self.ai_loading = False
                    status = result.get("status", "unknown")
                    if status == "ok":
                        self.ai_result = result["code"]
                        self.ai_options = self._split_ai_options(self.ai_result)
                        self.ai_option_intents = [self._extract_ai_intent(code) for code in self.ai_options[:2]]
                        self.ai_code_files = [self._save_ai_code(code) for code in self.ai_options[:2]]
                        self.ai_review_start = time.time()
                        self.log("AI_RESULT", f"status=ok, code_files={self.ai_code_files!r}")
                    else:
                        msg = result.get("msg", "")
                        self.ai_result = f"오류: {msg}"
                        self.ai_options = [self.ai_result, ""]
                        self.ai_option_intents = [self.ai_input_text, ""]
                        self.ai_review_start = time.time()
                        self.log("AI_RESULT", f"status={status}, msg={msg!r}")

            if (self.phase == "ai" and self.ai_result and not self.ai_loading
                    and time.time() - self.ai_review_start >= AI_REVIEW_SEC):
                self._start_ai_choice()

            if self.demo_mode:
                for s in np.random.normal(350, 50, 5):
                    self.ring.push(float(s))

            if self.phase == "preparing":
                # 4분면/입력바/하단바 없는 독립 페이지
                self.screen.fill(BG_COLOR)

                elapsed = time.time() - self.prepare_start
                remaining = PREPARE_DURATION_SEC - elapsed
                remaining_int = max(1, math.ceil(remaining))

                cx = self.screen_w // 2
                cy = self.screen_h // 2

                main_surf = self.font_item.render("준비 중", True, WHITE)
                self.screen.blit(main_surf, main_surf.get_rect(center=(cx, cy - 60)))

                cd_surf = self.font_target_title.render(f"{remaining_int}초 후 시작", True, WHITE)
                self.screen.blit(cd_surf, cd_surf.get_rect(center=(cx, cy + 60)))

                if remaining <= 0:
                    self._start_ssvep()
            elif self.phase == "ssvep":
                states = [((frame * f * 2 / FRAME_RATE) % 2) < 1 for f in FREQS]
                self._draw_all(ssvep_states=states)
                self._draw_top_bar()
                self._draw_bottom_bar()
            elif self.phase == "ai_choice":
                states = [((frame * f * 2 / FRAME_RATE) % 2) < 1 for f in FREQS]
                self._draw_all(ssvep_states=states)
                self._draw_top_bar()
                self._draw_bottom_bar()
            elif self.phase == "feedback":
                self._draw_all()

                rest_total = INTER_SELECTION_REST_SEC
                elapsed = time.time() - self.feedback_timer
                remaining = rest_total - elapsed
                remaining_int = max(1, math.ceil(remaining))

                cx = self.screen_w // 2
                cy = (self.grid_top + self.grid_bottom) // 2

                main_surf = self.font_item.render(self.feedback_text, True, GREEN)
                self.screen.blit(main_surf, main_surf.get_rect(center=(cx, cy - 30)))

                cd_surf = self.font_med.render(f"{remaining_int}초 후 다음 화면", True, GRAY)
                self.screen.blit(cd_surf, cd_surf.get_rect(center=(cx, cy + 60)))

                self._draw_top_bar()
                self._draw_bottom_bar()
                if remaining <= 0:
                    self._start_ssvep()
            elif self.phase == "timeout":
                # 4분면/입력바/하단바 없는 독립 페이지
                self.screen.fill(BG_COLOR)

                elapsed = time.time() - self.timeout_start
                remaining = TIMEOUT_REST_SEC - elapsed
                remaining_int = max(1, math.ceil(remaining))

                cx = self.screen_w // 2
                cy = self.screen_h // 2

                main_surf = self.font_item.render("검출 실패", True, WHITE)
                self.screen.blit(main_surf, main_surf.get_rect(center=(cx, cy - 100)))

                sub_surf = self.font_target_title.render("다시 시도하세요", True, WHITE)
                self.screen.blit(sub_surf, sub_surf.get_rect(center=(cx, cy)))

                cd_surf = self.font_target_title.render(f"{remaining_int}초 후 재시작", True, WHITE)
                self.screen.blit(cd_surf, cd_surf.get_rect(center=(cx, cy + 100)))

                if remaining <= 0:
                    if self.timeout_return_ai_choice:
                        self.timeout_return_ai_choice = False
                        self._start_ai_choice()
                    else:
                        self._start_ssvep()
            elif self.phase == "ai":
                self._draw_ai()
            elif self.phase == "ai_selected":
                self._draw_ai_selected()

            pygame.display.flip()
            frame += 1

    def cleanup(self):
        self.analyzer.stop()
        if self.eeg_recording_started:
            try:
                self.eeg.stop_recording()
            except Exception as e:
                print(f"\n[stop_recording 오류] {e}")
            self.eeg_recording_started = False
        try:
            self.eeg.close()
        except Exception as e:
            print(f"\n[ser close 오류] {e}")
        if not self.log_file.closed:
            self.log_file.close()
        pygame.quit()
        print(f"\n[종료] EEG : {self.eeg_path}")
        print(f"[종료] 로그: {self.log_path}")
        print(f"[종료] 입력: {self.menu.output!r}")


def prompt_subject_id():
    print()
    print("=" * 60)
    print("SSVEP Online 실험 (BCI 코딩)")
    print("=" * 60)
    sid = input("실험자 ID: ").strip()
    return sid if sid else "01"


def prompt_eeg_port():
    port_input = input(f"EEG 시리얼 포트 [Enter = {DEFAULT_EEG_PORT}]: ").strip()
    return port_input if port_input else DEFAULT_EEG_PORT


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BCI 온라인 모드 (FBCCA)")
    parser.add_argument("--demo", action="store_true",
                        help="EEG 보드 없이 UI만 테스트")
    args = parser.parse_args()

    subject_id = prompt_subject_id()
    eeg_port = prompt_eeg_port()

    exp = OnlineExperiment(
        subject=subject_id,
        port=eeg_port,
        demo_mode=args.demo,
    )
    exp.run()
