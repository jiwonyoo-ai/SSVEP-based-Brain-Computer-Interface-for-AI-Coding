"""
ssvep_training.py — SSVEP 전용 자극 + EEG 수집
=================================================================
[변경 사항]
  - P300 단계 완전 제거
  - SSVEP 자극만 진행
  - 시행 시간 단축 (P300 없어서 약 8초/시행)

[흐름]
  1. 실험자 ID 입력
  2. 베이스라인 (120초)
  3. 사이클 반복:
       각 시행:
         ① 시행 안내 (3초)
         ② Fixation cross (1초)
         ③ SSVEP 자극 (4초, 4분면 깜빡임)
         ④ 시행 간 휴식 (3초)
  4. 종료

[설정]
  SSVEP 주파수: 9.25, 10, 12, 15 Hz
  6 사이클 × 4 시행 = 24 시행
  시행당 약 8초, 총 약 7~8분

[저장 파일]
  recordings/sub{ID}/sub{ID}_training_{YYYYMMDD}_{HHmm}.csv
  recordings/sub{ID}/sub{ID}_training_{YYYYMMDD}_{HHmm}_events.csv

[조작]
  Space : 시작
  Esc   : 즉시 종료
  F     : Fast 모드 (1/5 속도, 개발용)
"""

import pygame
import random
import sys
import csv
import os
import time
from datetime import datetime

try:
    from eeg_collector import EEGCollector
    EEG_AVAILABLE = True
except ImportError:
    EEG_AVAILABLE = False
    print("[경고] eeg_collector.py 없음 — EEG 수집 안 됨")

# ============================================================
# 설정
# ============================================================
RECORDINGS_BASE_DIR = "recordings"
DEFAULT_EEG_PORT    = "COM3"

SCREEN_W, SCREEN_H = 1100, 850
FRAME_RATE = 60

FREQS          = [9.25, 10, 12, 15]
SSVEP_DURATION = 4.0

TRIAL_INTRO_DURATION = 3.0
FIXATION_DURATION    = 1.0
INTER_TRIAL_REST     = 3.0
INTER_CYCLE_REST     = 3.0
BASELINE_DURATION    = 120.0
TRIALS_PER_CYCLE     = 4
NUM_CYCLES           = 6

QUADRANT_LABELS = ["A ~ I", "J ~ R", "S ~ Z", "기능키"]
QUADRANT_NAMES  = ["좌상", "우상", "좌하", "우하"]

BG_COLOR     = (30,  30,  30)
DIM_RECT     = (60,  60,  60)
BRIGHT_RECT  = (180, 180, 180)
DIM_TEXT     = (50,  50,  50)
BRIGHT_TEXT  = (200, 200, 200)
LINE_COLOR   = (50,  50,  50)
WHITE        = (240, 240, 240)
TARGET_COLOR = (255, 180,  80)
GRAY         = (120, 120, 120)

TOP_BAR_H    = 50
BOTTOM_BAR_H = 50
GRID_TOP     = TOP_BAR_H
GRID_BOTTOM  = SCREEN_H - BOTTOM_BAR_H
GRID_H       = GRID_BOTTOM - GRID_TOP

CENTERS = [
    (SCREEN_W // 4,     GRID_TOP + GRID_H // 4),
    (SCREEN_W * 3 // 4, GRID_TOP + GRID_H // 4),
    (SCREEN_W // 4,     GRID_TOP + GRID_H * 3 // 4),
    (SCREEN_W * 3 // 4, GRID_TOP + GRID_H * 3 // 4),
]
CELL_W = SCREEN_W // 2 - 30
CELL_H = GRID_H // 2 - 30


# ============================================================
# Experiment 클래스
# ============================================================
class Experiment:
    def __init__(self, subject_id, eeg_port=DEFAULT_EEG_PORT):
        self.subject_id = subject_id
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption(f"SSVEP Training — sub{subject_id}")
        self.clock     = pygame.time.Clock()
        self.font_item = pygame.font.SysFont('malgun gothic', 80, bold=True)
        self.font_med  = pygame.font.SysFont('malgun gothic', 30, bold=True)
        self.font_sml  = pygame.font.SysFont('malgun gothic', 20)
        self.font_big  = pygame.font.SysFont('malgun gothic', 80, bold=True)
        self.fast_mode = False

        # 사이클 순서
        self.cycles = []
        for _ in range(NUM_CYCLES):
            order = [0, 1, 2, 3]
            random.shuffle(order)
            self.cycles.append(order)

        # 저장 경로
        sub_dir = os.path.join(RECORDINGS_BASE_DIR, f"sub{subject_id}")
        os.makedirs(sub_dir, exist_ok=True)
        ts          = datetime.now().strftime("%Y%m%d_%H%M")
        base_name   = f"sub{subject_id}_training_{ts}"
        self.eeg_path    = os.path.join(sub_dir, f"{base_name}.csv")
        self.events_path = os.path.join(sub_dir, f"{base_name}_events.csv")

        # 이벤트 로그
        self.events_file   = open(self.events_path, 'w', newline='', encoding='utf-8')
        self.events_writer = csv.writer(self.events_file)
        self.events_writer.writerow([
            "timestamp", "event", "trial_global", "cycle",
            "trial_in_cycle", "target_quadrant", "data"
        ])

        # EEG 수집기
        self.eeg = None
        if EEG_AVAILABLE:
            self.eeg = EEGCollector(port=eeg_port)
            if not self.eeg.connect():
                print("[경고] EEG 연결 실패 — 자극만 진행")
                self.eeg = None

    # ── 유틸 ──
    def time_scale(self, t):
        return t * 0.2 if self.fast_mode else t

    def log_event(self, event_type, trial_global=0, cycle=0,
                  trial_in_cycle=0, target=0, data=""):
        ts = datetime.now().strftime("%Y %m %d %H:%M:%S.%f")
        self.events_writer.writerow(
            [ts, event_type, trial_global, cycle, trial_in_cycle, target, data])
        self.events_file.flush()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.cleanup(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.cleanup(); sys.exit()
                if event.key == pygame.K_f:
                    self.fast_mode = not self.fast_mode

    # ── 그리기 ──
    def draw_quadrant(self, idx, ssvep_on=False, highlight=False):
        cx, cy = CENTERS[idx]
        rect   = pygame.Rect(cx - CELL_W//2, cy - CELL_H//2, CELL_W, CELL_H)
        if highlight:
            bg, fg = TARGET_COLOR, (0, 0, 0)
        elif ssvep_on:
            bg, fg = BRIGHT_RECT, (0, 0, 0)
        else:
            bg, fg = DIM_RECT, BRIGHT_TEXT
        pygame.draw.rect(self.screen, bg, rect, border_radius=14)
        surf = self.font_item.render(QUADRANT_LABELS[idx], True, fg)
        self.screen.blit(surf, surf.get_rect(center=(cx, cy)))
        freq_surf = self.font_sml.render(f"{FREQS[idx]}Hz", True, GRAY)
        self.screen.blit(freq_surf, (cx - CELL_W//2 + 10, cy - CELL_H//2 + 8))

    def draw_all(self, ssvep_states=None, highlight_quad=None):
        self.screen.fill(BG_COLOR)
        pygame.draw.line(self.screen, LINE_COLOR,
                         (SCREEN_W//2, GRID_TOP), (SCREEN_W//2, GRID_BOTTOM), 3)
        pygame.draw.line(self.screen, LINE_COLOR,
                         (0, (GRID_TOP+GRID_BOTTOM)//2),
                         (SCREEN_W, (GRID_TOP+GRID_BOTTOM)//2), 3)
        for i in range(4):
            s_on = ssvep_states[i] if ssvep_states else False
            hl   = (highlight_quad == i)
            self.draw_quadrant(i, ssvep_on=s_on, highlight=hl)

    def draw_status(self, text, color=WHITE):
        surf = self.font_med.render(text, True, color)
        self.screen.blit(surf, (15, 15))

    def draw_center_text(self, text, color=WHITE):
        surf = self.font_big.render(text, True, color)
        self.screen.blit(surf, surf.get_rect(center=(SCREEN_W//2, SCREEN_H//2)))

    def wait(self, duration):
        t0 = time.time()
        while time.time() - t0 < self.time_scale(duration):
            self.handle_events()
            pygame.display.flip()
            self.clock.tick(FRAME_RATE)

    # ── 단계별 ──
    def run_intro(self):
        waiting = True
        while waiting:
            self.handle_events()
            self.screen.fill(BG_COLOR)
            lines = [
                "SSVEP 뇌파 수집 실험",
                "",
                f"SSVEP: {NUM_CYCLES}사이클 × 4시행 = {NUM_CYCLES*4}시행",
                f"자극 주파수: {FREQS} Hz",
                "",
                "화면에 표시되는 분면을 주시해 주세요.",
                "",
                "준비되면 Space를 눌러 시작하세요.",
            ]
            y = SCREEN_H // 2 - len(lines) * 22
            for line in lines:
                s = self.font_med.render(line, True, WHITE)
                self.screen.blit(s, s.get_rect(center=(SCREEN_W//2, y))); y += 44
            pygame.display.flip()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.cleanup(); sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.cleanup(); sys.exit()
                    if event.key == pygame.K_SPACE:
                        waiting = False
                    if event.key == pygame.K_f:
                        self.fast_mode = not self.fast_mode
            self.clock.tick(FRAME_RATE)

    def run_baseline(self):
        self.log_event("BASELINE_START")
        t0 = time.time()
        dur = self.time_scale(BASELINE_DURATION)
        while time.time() - t0 < dur:
            self.handle_events()
            self.screen.fill(BG_COLOR)
            elapsed  = time.time() - t0
            remain   = max(0, dur - elapsed)
            self.draw_center_text("+", WHITE)
            status = f"베이스라인 — 눈 감고 휴식  ({int(remain)}초 남음)"
            self.draw_status(status, GRAY)
            pygame.display.flip()
            self.clock.tick(FRAME_RATE)
        self.log_event("BASELINE_END")

    def run_trial_intro(self, trial_global, cycle, trial_in_cycle, target):
        t0  = time.time()
        dur = self.time_scale(TRIAL_INTRO_DURATION)
        while time.time() - t0 < dur:
            self.handle_events()
            self.draw_all(highlight_quad=target)
            status = (f"시행 {trial_global+1}/{NUM_CYCLES*4}  "
                      f"[{QUADRANT_NAMES[target]}] 분면을 주시하세요")
            self.draw_status(status, TARGET_COLOR)
            pygame.display.flip()
            self.clock.tick(FRAME_RATE)

    def run_fixation(self):
        t0  = time.time()
        dur = self.time_scale(FIXATION_DURATION)
        while time.time() - t0 < dur:
            self.handle_events()
            self.draw_all()
            self.draw_center_text("+", WHITE)
            pygame.display.flip()
            self.clock.tick(FRAME_RATE)

    def run_ssvep(self, trial_global, cycle, trial_in_cycle, target):
        self.log_event("SSVEP_START", trial_global, cycle, trial_in_cycle, target)
        t0  = time.time()
        dur = self.time_scale(SSVEP_DURATION)
        while time.time() - t0 < dur:
            self.handle_events()
            elapsed = time.time() - t0
            frame   = int(elapsed * FRAME_RATE)
            states  = [((frame * f * 2 / FRAME_RATE) % 2) < 1 for f in FREQS]
            self.draw_all(ssvep_states=states)
            remain = max(0, dur - elapsed)
            self.draw_status(
                f"SSVEP [{QUADRANT_NAMES[target]}]  {remain:.1f}s", WHITE)
            pygame.display.flip()
            self.clock.tick(FRAME_RATE)
        self.log_event("SSVEP_END", trial_global, cycle, trial_in_cycle, target)

    def run_rest(self, duration, label="휴식"):
        t0  = time.time()
        dur = self.time_scale(duration)
        while time.time() - t0 < dur:
            self.handle_events()
            self.screen.fill(BG_COLOR)
            remain = max(0, dur - (time.time() - t0))
            self.draw_status(f"{label}  ({remain:.1f}초)", GRAY)
            pygame.display.flip()
            self.clock.tick(FRAME_RATE)

    # ── 전체 실행 ──
    def run(self):
        self.run_intro()

        if self.eeg:
            self.eeg.start_recording(self.eeg_path)

        self.log_event("EXPERIMENT_START")
        self.run_baseline()

        trial_global = 0
        for cycle_idx, trial_order in enumerate(self.cycles):
            self.log_event("CYCLE_START", data=f"cycle={cycle_idx}")
            for trial_in_cycle, target in enumerate(trial_order):
                self.run_trial_intro(trial_global, cycle_idx, trial_in_cycle, target)
                self.run_fixation()
                self.run_ssvep(trial_global, cycle_idx, trial_in_cycle, target)
                is_last = (trial_in_cycle == TRIALS_PER_CYCLE - 1)
                if not is_last:
                    self.run_rest(INTER_TRIAL_REST, "시행 간 휴식")
                trial_global += 1
            self.log_event("CYCLE_END", data=f"cycle={cycle_idx}")
            if cycle_idx < NUM_CYCLES - 1:
                self.run_rest(INTER_CYCLE_REST, "사이클 간 휴식")

        self.log_event("EXPERIMENT_END")
        self.cleanup()

    def cleanup(self):
        if self.eeg:
            self.eeg.stop_recording()
            self.eeg.close()
        if not self.events_file.closed:
            self.events_file.close()
        pygame.quit()
        print(f"\n수집 완료!")
        print(f"  EEG    : {self.eeg_path}")
        print(f"  Events : {self.events_path}")


# ============================================================
# 진입점
# ============================================================
if __name__ == "__main__":
    subject_id = input("실험자 ID 입력 (예: A, 01): ").strip() or "A"
    port       = input(f"EEG 포트 (기본 {DEFAULT_EEG_PORT}): ").strip() or DEFAULT_EEG_PORT
    exp = Experiment(subject_id=subject_id, eeg_port=port)
    exp.run()
