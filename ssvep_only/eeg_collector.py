"""
EEG 데이터 수집기 (한백전자 IoT Smart Health Lab용) - 최종 v2
=================================================================

[프로그램 작동 방식]
  1. 실행하면 자동으로 설정된 시리얼 포트(COM3) 와 연결됩니다.
  2. 연결 성공 후 메뉴가 뜹니다:
        s : 새 녹화 시작 (CSV 파일 자동 생성, 파일명에 타임스탬프 부여)
        x : 프로그램 완전 종료 (시리얼 포트 안전하게 닫음)
  3. 's' 입력 시 백그라운드 스레드가 시리얼 데이터 수신 + CSV 저장 시작.
        화면에는 실시간 상태(최근값/총샘플/Hz/오류) 가 표시됩니다.
  4. 녹화 중 'q' + Enter 입력 → 정지. 파일 저장 후 메뉴로 복귀.
        ('q' 외 다른 키는 무시됨 — 실수 방지)
  5. 다시 's' 누르면 새 파일로 또 녹화 가능 (반복 녹화 지원).
  6. 'x' 입력 시 프로그램 종료.
  7. Ctrl+C 눌러도 안전하게 정리 후 종료됨.

[실행 시 화면 예시]
  >>> [COM3] 연결 성공. 준비 완료!

  [s: 수집 시작 / x: 프로그램 종료] : s

  [기록 시작] 파일명: eeg_data_1745920000.csv
  >>> 'q' + Enter 를 누르면 정지합니다.
  수집 중: 최근값   416  |  샘플    140개  |  220.45 Hz  |  오류 0개
                              ↑ 같은 줄이 0.1초마다 갱신됨

  (사용자가 'q' + Enter 입력)

  [기록 종료] 패킷 100개 / 샘플 1400개 (오류 0개) — 파일이 안전하게 저장되었습니다.

  [s: 수집 시작 / x: 프로그램 종료] : x
  프로그램을 종료합니다.
  >>> 시리얼 포트가 안전하게 닫혔습니다.

[코드 구성]
  - 설정부 (PORT, BAUD_RATE 등 상수)
  - EEGCollector 클래스
        connect()         : 시리얼 연결
        close()           : 시리얼 정리
        _record_loop()    : [백그라운드 스레드] 시리얼 수신 + CSV 저장
        start_recording() : 녹화 스레드 시작
        stop_recording()  : 정지 신호 + 스레드 종료 대기
  - main() 함수: 메뉴 루프 (s/x 입력 처리, KeyboardInterrupt 예외 처리)

[패킷 프로토콜] (아두이노 펌웨어 기준)
  전체 패킷: 33 byte
    byte[0]    = 0xFF                    (헤더)
    byte[1..4] = millis() 타임스탬프      (32-bit big-endian)
    byte[5..6] = 샘플 1번  (16-bit BE)
    byte[7..8] = 샘플 2번
    ...
    byte[31..32] = 샘플 14번
  → 패킷당 14개 샘플

[CSV 포맷] (한백 공식 데이터 호환)
  헤더 줄: time,mV
  빈 줄
  패킷마다: 첫 행 = '<timestamp>,<sample1>'
            그 다음 13행 = ',<sampleN>'  (timestamp 비움)

[타임스탬프 주의사항 — 분석 시 인지]
  CSV 의 timestamp 는 'PC가 패킷을 받은 시각' 이지
  'EEG 센서가 측정한 시각' 이 아닙니다.
  USB 시리얼 버퍼링 + OS 스케줄링으로 약간의 jitter 존재.
  정확한 시간축이 필요한 분석(FFT 등) 에서는
    실제시각[i] ≈ packet_timestamp + i × (1/샘플레이트)
  형태로 보간하여 사용하세요.
"""

import serial
import csv
import time
import threading
import struct
import sys
from datetime import datetime

# ===== 설정 =====
PORT = 'COM3'
BAUD_RATE = 115200
PACKET_HEADER = b'\xff'
PACKET_SIZE = 32                  # 헤더 제외 페이로드 크기
SAMPLES_PER_PACKET = 14           # 패킷당 EEG 샘플 개수
SERIAL_TIMEOUT = 1                # 시리얼 read 타임아웃 (초)
DISPLAY_INTERVAL = 0.1            # 화면 출력 주기 (초) -- 10 Hz 갱신
FLUSH_INTERVAL = 1.0              # CSV flush 주기 (초)
TIMESTAMP_FORMAT = '%Y %m %d %H:%M:%S.%f'   # 한백 포맷
# =================


class EEGCollector:
    def __init__(self, port=PORT, baud=BAUD_RATE):
        self.port = port
        self.baud = baud
        self.ser = None

        self.stop_event = threading.Event()
        self.thread = None

        # 통계
        self.sample_count = 0
        self.packet_count = 0
        self.error_count = 0

    # ---------- 연결 / 종료 ----------
    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=SERIAL_TIMEOUT)
            time.sleep(2)                 # 아두이노 리셋 대기
            self.ser.reset_input_buffer()
            print(f">>> [{self.port}] 연결 성공. 준비 완료!")
            return True
        except Exception as e:
            print(f">>> 연결 실패: {e}")
            return False

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            print(">>> 시리얼 포트가 안전하게 닫혔습니다.")

    # ---------- 백그라운드 수신 루프 ----------
    def _record_loop(self, filename, on_sample):
        """
        시리얼에서 패킷을 받아서:
          - filename 이 주어지면  → CSV 로 저장
          - on_sample 이 주어지면 → 샘플마다 콜백 호출 (실시간 ring buffer push 등)
        둘 다 None 일 수도, 둘 다 줄 수도 있음.
        """
        last_print = 0.0
        last_flush = 0.0
        start_time = None

        f = None
        writer = None
        try:
            if filename:
                f = open(filename, 'w', newline='')
                writer = csv.writer(f)
                # 한백 공식 포맷: 헤더 + 빈 줄
                writer.writerow(["time", "mV"])
                writer.writerow([])

            while not self.stop_event.is_set():
                if self.ser.in_waiting <= 0:
                    continue

                # 헤더 동기화
                if self.ser.read(1) != PACKET_HEADER:
                    continue

                # 페이로드 수신 + 길이 검증
                payload = self.ser.read(PACKET_SIZE)
                if len(payload) < PACKET_SIZE:
                    self.error_count += 1
                    continue

                # 패킷 도착 시각 (PC 시각)
                packet_dt = datetime.now()
                if start_time is None:
                    start_time = time.time()

                # 패킷 파싱
                # payload[0:4]   = millis() (필요 시 활용)
                # payload[4:32]  = 14 × 2B 샘플 (big-endian)
                try:
                    samples = struct.unpack('>14H', payload[4:32])
                except struct.error:
                    self.error_count += 1
                    continue

                # CSV 작성: 첫 행 timestamp+샘플1, 나머지 13행은 timestamp 빈칸
                if writer is not None:
                    ts_str = packet_dt.strftime(TIMESTAMP_FORMAT)
                    writer.writerow([ts_str, samples[0]])
                    for s in samples[1:]:
                        writer.writerow(["", s])

                # 실시간 콜백: 샘플 14개를 도착 순서대로 콜백에 전달
                if on_sample is not None:
                    for s in samples:
                        try:
                            on_sample(float(s))
                        except Exception as e:
                            # 콜백 오류가 수집 자체를 망가뜨리지 않도록 흡수
                            print(f"\n[on_sample 콜백 오류] {e}")

                self.sample_count += SAMPLES_PER_PACKET
                self.packet_count += 1

                now = time.time()

                # 화면 출력 throttle (10Hz 갱신)
                if now - last_print >= DISPLAY_INTERVAL:
                    elapsed = now - start_time
                    hz = self.sample_count / elapsed if elapsed > 0 else 0
                    print(f"\r수집 중: 최근값 {samples[-1]:5d}  |  "
                          f"샘플 {self.sample_count:6d}개  |  "
                          f"{hz:6.2f} Hz  |  "
                          f"오류 {self.error_count}개   ",
                          end='', flush=True)
                    last_print = now

                # 주기적 flush (정전 시 데이터 손실 최소화)
                if writer is not None and now - last_flush >= FLUSH_INTERVAL:
                    f.flush()
                    last_flush = now

        except serial.SerialException as e:
            print(f"\n[시리얼 오류] {e}")
            self.stop_event.set()
        except Exception as e:
            print(f"\n[수집 스레드 예외] {e}")
            self.stop_event.set()
        finally:
            if f is not None:
                f.close()

    # ---------- 녹화 시작/정지 ----------
    def start_recording(self, filename=None, on_sample=None):
        """
        EEG 수집 시작.
          filename  : CSV 저장 경로 (None 이면 저장 안 함 — 실시간 스트리밍 전용)
          on_sample : 샘플 1개당 호출되는 콜백 (예: ring_buffer.push)
        둘 중 적어도 하나는 줘야 의미가 있음.
        """
        if not self.ser or not self.ser.is_open:
            print(">>> 오류: 시리얼 포트가 연결되지 않았습니다.")
            return False

        self.sample_count = 0
        self.packet_count = 0
        self.error_count = 0
        self.stop_event.clear()

        # 메뉴에서 머무는 동안 쌓인 오래된 데이터 제거
        self.ser.reset_input_buffer()

        self.thread = threading.Thread(
            target=self._record_loop,
            args=(filename, on_sample),
            daemon=True,
        )
        self.thread.start()
        if filename:
            print(f"\n[기록 시작] 파일명: {filename}")
        else:
            print(f"\n[스트리밍 시작] CSV 저장 없이 실시간 콜백 모드")
        if on_sample is not None:
            print(">>> 실시간 콜백 활성화 — ring buffer 등으로 샘플 push 중")
        print(">>> 'q' + Enter 를 누르면 정지합니다.")
        return True

    def stop_recording(self):
        self.stop_event.set()
        if self.thread is not None:
            self.thread.join(timeout=3)
        print(f"\n[기록 종료] 패킷 {self.packet_count}개 / 샘플 {self.sample_count}개 "
              f"(오류 {self.error_count}개) — 파일이 안전하게 저장되었습니다.")


# ---------- 메인 실행부 ----------
def main():
    collector = EEGCollector()
    if not collector.connect():
        sys.exit(1)

    try:
        while True:
            menu = input("\n[s: 수집 시작 / x: 프로그램 종료] : ").strip().lower()

            if menu == 's':
                fname = f"eeg_data_{int(time.time())}.csv"
                if not collector.start_recording(fname):
                    continue

                while True:
                    try:
                        cmd = input().strip().lower()
                    except EOFError:
                        cmd = 'q'
                    if cmd == 'q':
                        break
                    print(">>> 'q' + Enter 를 입력해야 정지됩니다.")

                collector.stop_recording()

            elif menu == 'x':
                print("프로그램을 종료합니다.")
                break

            else:
                print("알 수 없는 명령입니다. 's' 또는 'x' 를 입력하세요.")

    except KeyboardInterrupt:
        print("\n[Ctrl+C 감지] 안전하게 종료합니다...")
        collector.stop_event.set()
        if collector.thread is not None and collector.thread.is_alive():
            collector.thread.join(timeout=3)

    finally:
        collector.close()


if __name__ == "__main__":
    main()