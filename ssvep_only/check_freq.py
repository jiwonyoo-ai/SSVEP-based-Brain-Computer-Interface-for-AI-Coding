"""
check_freq.py — 실시간 주파수 진단 (ring buffer 또는 실제 EEG)
================================================================
실행:
  python check_freq.py          # 실제 EEG (COM3)
  python check_freq.py --demo   # 데모 모드 (sin 파형 주입)
  python check_freq.py --demo --freq 12.0   # 12Hz sin 주입

화면 출력 예시:
  [버퍼: 843/843]  분석 가능
  9.25Hz : ████████████████░░░░  score=1.834  prob=67.3%  ← 최고
  10.00Hz: ░░░░░░░░░░░░░░░░░░░░  score=0.006  prob=10.8%
  12.00Hz: ░░░░░░░░░░░░░░░░░░░░  score=0.005  prob=10.8%
  15.00Hz: ░░░░░░░░░░░░░░░░░░░░  score=0.011  prob=10.9%
  → 판정: 9.25Hz (conf=67.3%) ✓ THRESHOLD 통과
"""
import argparse
import time
import numpy as np
from collections import deque
import threading
import csv                 # [추가] CSV 저장을 위한 모듈
from datetime import datetime # [추가] 시간 기록을 위한 모듈
import os                  # [추가] 파일 존재 여부 확인을 위한 모듈

FREQS = [9.25, 10.0, 12.0, 15.0]
FS = 222
WINDOW_SEC = 3.8
WINDOW_SAMPLES = int(FS * WINDOW_SEC)  # 843
CONF_THRESHOLD = 0.6
PORT = "COM3"
BAR_WIDTH = 20

# [추가] 저장될 파일명 설정
SAVE_FILENAME = "ssvep_results.csv"

def save_to_csv(data_dict):
    """[추가] 결과를 CSV 파일에 한 줄씩 추가 저장하는 함수"""
    file_exists = os.path.isfile(SAVE_FILENAME)
    # utf-8-sig는 엑셀에서 한글 깨짐을 방지합니다.
    with open(SAVE_FILENAME, mode='a', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=data_dict.keys())
        if not file_exists:
            writer.writeheader()  # 파일이 처음 생길 때만 제목줄 작성
        writer.writerow(data_dict)

def make_bar(ratio, width=BAR_WIDTH):
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)


def run_demo(demo_freq):
    """sin 파형을 ring buffer에 실시간으로 push하며 분석"""
    from ssvep_fbcca import FBCCA

    ring = deque(maxlen=WINDOW_SAMPLES * 2)
    clf = FBCCA(freqs=FREQS, fs=FS)
    idx = 0

    print(f"\n[DEMO 모드] {demo_freq}Hz sin 파형 주입 중 (Ctrl+C 로 종료)\n")

    try:
        while True:
            for i in range(14):
                t = idx / FS
                s = (350
                     + 60 * np.sin(2 * np.pi * demo_freq * t)
                     + 20 * np.sin(2 * np.pi * demo_freq * 2 * t)
                     + np.random.normal(0, 8))
                ring.append(s)
                idx += 1

            buf_len = len(ring)

            if buf_len >= WINDOW_SAMPLES:
                window = np.array(list(ring)[-WINDOW_SAMPLES:], dtype=np.float32).reshape(1, -1)
                try:
                    scores = clf._compute_scores(window)
                    probs = clf.predict_proba(window)
                except Exception as e:
                    print(f"\n[FBCCA 오류] {e}")
                    time.sleep(0.1)
                    continue

                best_idx = int(np.argmax(probs))
                best_prob = float(probs[best_idx])
                passed = best_prob >= CONF_THRESHOLD

                # [추가] 데모 결과 저장 로직
                result_data = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "mode": "DEMO",
                    "input_freq": demo_freq,
                    "pred_freq": FREQS[best_idx],
                    "probability": round(best_prob, 4),
                    "is_passed": passed,
                    "is_correct": abs(demo_freq - FREQS[best_idx]) < 0.01
                }
                save_to_csv(result_data)

                # 화면 출력 부분
                print("\033[2J\033[H", end="")
                print(f"[DEMO] 주입: {demo_freq}Hz | 버퍼: {buf_len}/{WINDOW_SAMPLES} (결과 저장됨)\n")
                for i, (f, sc, pr) in enumerate(zip(FREQS, scores, probs)):
                    bar = make_bar(pr)
                    marker = "← 최고" if i == best_idx else ""
                    print(f"  {f:5.2f}Hz : {bar}  score={sc:.3f}  prob={pr*100:.1f}%  {marker}")

                status = "✓ 통과" if passed else "✗ 미달"
                print(f"\n  → 판정: {FREQS[best_idx]}Hz ({best_prob*100:.1f}%) {status}")

            time.sleep(1.0 / 60)

    except KeyboardInterrupt:
        print("\n\n[종료]")


def run_eeg(port):
    """실제 EEG로부터 ring buffer에 push하며 분석"""
    from ssvep_fbcca import FBCCA
    from eeg_collector import EEGCollector

    ring = deque(maxlen=WINDOW_SAMPLES * 2)
    clf = FBCCA(freqs=FREQS, fs=FS)

    def on_sample(s):
        ring.append(s)

    collector = EEGCollector(port=port)
    if not collector.connect():
        print("[오류] EEG 연결 실패")
        return

    collector.start_recording(on_sample=on_sample)
    print(f"\n[EEG 모드] {port} 연결됨. (Ctrl+C 종료)\n")

    try:
        while True:
            buf_len = len(ring)
            if buf_len >= WINDOW_SAMPLES:
                window = np.array(list(ring)[-WINDOW_SAMPLES:], dtype=np.float32).reshape(1, -1)
                try:
                    scores = clf._compute_scores(window)
                    probs = clf.predict_proba(window)
                except Exception as e:
                    print(f"\n[FBCCA 오류] {e}")
                    time.sleep(1.0)
                    continue

                best_idx = int(np.argmax(probs))
                best_prob = float(probs[best_idx])
                passed = best_prob >= CONF_THRESHOLD

                # [추가] 실시간 EEG 결과 저장 로직
                result_data = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "mode": "EEG",
                    "input_freq": "N/A", 
                    "pred_freq": FREQS[best_idx],
                    "probability": round(best_prob, 4),
                    "is_passed": passed,
                    "is_correct": "N/A"
                }
                save_to_csv(result_data)

                # 화면 출력 부분
                print("\033[2J\033[H", end="")
                print(f"[EEG] 버퍼: {buf_len}/{WINDOW_SAMPLES} (결과 저장됨)\n")
                for i, (f, sc, pr) in enumerate(zip(FREQS, scores, probs)):
                    bar = make_bar(pr)
                    marker = "← 최고" if i == best_idx else ""
                    print(f"  {f:5.2f}Hz : {bar}  score={sc:.3f}  prob={pr*100:.1f}%  {marker}")

                status = "✓ 통과" if passed else "✗ 미달"
                print(f"\n  → 판정: {FREQS[best_idx]}Hz ({best_prob*100:.1f}%) {status}")
            else:
                print(f"\r[버퍼 채우는 중: {buf_len}/{WINDOW_SAMPLES}]", end="", flush=True)

            time.sleep(1.0)

    except KeyboardInterrupt:
        print("\n\n[종료]")
    finally:
        collector.stop_recording()
        collector.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="데모 모드")
    parser.add_argument("--freq", type=float, default=9.25, help="데모 주파수")
    parser.add_argument("--port", type=str, default=PORT, help="포트")
    args = parser.parse_args()

    if args.demo:
        run_demo(args.freq)
    else:
        run_eeg(args.port)