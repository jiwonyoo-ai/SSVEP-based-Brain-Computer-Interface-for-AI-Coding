"""
ai_coder.py — Claude API 클라이언트 (BCI 온라인 모드 전용)
=================================================================
[역할]
  사용자가 BCI 로 입력한 짧은 자연어 명령(예: "파이썬으로 hello 출력")을
  받아서 Claude API 에 전달하고, 생성된 파이썬 코드를 받아서 반환.

[비동기 패턴]
  generate(text)   → 백그라운드 스레드에서 API 호출 시작 (즉시 반환)
  get_result()     → 매 프레임 폴링. 완료 전이면 None, 완료되면 dict.

  이 패턴은 pygame UI 가 블로킹되지 않게 하기 위함.
  stimulus_online.py 의 메인 루프에서 60 FPS 로 get_result() 를 부름.

[API 키 설정]
  환경변수 ANTHROPIC_API_KEY 에서 자동 로드.
  작업 폴더의 .env 파일에 ANTHROPIC_API_KEY=... 형식으로 저장해도 자동 로드.
  키가 없거나 anthropic 패키지가 설치되어 있지 않으면 → stub 모드 자동 활성화
  (1초 후 더미 코드 반환, UI 흐름 테스트 가능).

[Stub 모드]
  실제 API 호출 없이 더미 응답을 줍니다. 다음 상황에서 자동 진입:
    - ANTHROPIC_API_KEY 환경변수 미설정
    - anthropic 패키지 미설치 (pip install anthropic)
  API 호출 중 예외(네트워크 오류 등)는 {'status': 'err', 'msg': str} 로 반환.

[반환 형식]
  get_result() 결과:
    None                           → 아직 처리 중
    {'status': 'ok',  'code': str} → 정상 완료
    {'status': 'err', 'msg':  str} → 오류
"""
import os
import time
import threading


# ===== 모델 / API 설정 =====
MODEL_NAME = "claude-sonnet-4-6"
MAX_TOKENS = 2048
STUB_DELAY_SEC = 1.0                  # stub 모드에서 더미 응답까지 대기

# 시스템 프롬프트 — Claude 에 어떤 역할을 부여할지
SYSTEM_PROMPT = (
    "당신은 BCI(뇌-컴퓨터 인터페이스) 전문 코딩 어시스턴트입니다.\n"
    "사용자는 SSVEP를 통해 한 글자씩 어렵게 명령을 입력합니다.\n"
    "입력은 주로 영어 대문자 단어, 짧은 영어 조각, 숫자, 공백으로 구성되며, "
    "오타, 누락, 공백 부족, 불완전한 문장이 포함될 수 있습니다.\n\n"
    "매뉴얼:\n"
    "1. [의도 파악] 입력된 짧은 영어 단어나 불완전한 명령을 "
    "가장 가능성 높은 Python 코딩 명령으로 해석하세요.\n"
    "   예: 'HELLO' -> 'Python으로 Hello World를 출력하는 코드 작성'\n"
    "   예: 'SUM 1 10' -> 'Python으로 1부터 10까지의 합을 출력하는 코드 작성'\n"
    "   예: 'RANDOM NUM' -> 'Python으로 임의의 숫자를 출력하는 코드 작성'\n"
    "   예: 'PLOT SIN' -> 'Python으로 사인파를 그리는 코드 작성'\n"
    "2. [코드 생성] 해석된 의도를 바탕으로 짧고 독립 실행 가능한 Python 코드를 작성하세요.\n"
    "3. [안전성] 파일 삭제, 시스템 설정 변경, 네트워크 요청, 외부 프로그램 실행은 "
    "사용자가 명확히 요구하지 않으면 하지 마세요.\n"
    "4. [출력 형식] 기본적으로 설명이나 마크업(```python) 없이 오직 순수 Python 코드만 반환하세요.\n"
    "   단, 사용자가 코드 후보 2개를 요청하면 두 후보는 코드 구조뿐 아니라 입력에 대한 해석/보정 문장 자체가 달라야 합니다.\n"
    "   - CODE 1: 입력을 가장 단순하고 직접적인 의미로 해석한 코드입니다. 콘솔에서 실행 가능한 직관적 코드로 작성하세요.\n"
    "   - CODE 2: 입력을 다르게 해석할 수 있는 합리적인 대안 의도의 코드입니다. CODE 1과 '# 의도:' 문장이 반드시 달라야 합니다.\n"
    "   사용자가 명확히 GUI, 웹, 파일 저장을 요구하지 않으면 tkinter, 웹 서버, 파일 입출력 코드는 작성하지 마세요.\n"
    "   단순히 print를 함수로 감싸거나, def/main/while만 추가하거나, 변수명만 바꾼 중복 후보는 만들지 마세요.\n"
    "   출력은 '### CODE 1'과 '### CODE 2' 구분자 아래에 각각 순수 Python 코드만 작성하세요.\n"
    "5. [의도 주석] 각 코드 첫 줄에 '# 의도: [보정된 한국어 의도]' 형식으로 한 줄 주석을 달아주세요.\n"
    "6. [주석] 나머지 주석도 한국어로 간결하게 작성하세요."
)


# ============================================================
# .env 로드 (python-dotenv 없이 최소 구현)
# ============================================================
def _load_dotenv(path=".env"):
    """
    작업 폴더의 .env 파일을 읽어 os.environ 에 없는 값만 채움.
    API 키 값은 출력하지 않음.
    """
    if not os.path.exists(path):
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except Exception as e:
        print(f"[ai_coder] .env 로드 실패: {e}")


_load_dotenv()


# ============================================================
# Anthropic 패키지 import (없어도 동작)
# ============================================================
try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    Anthropic = None
    ANTHROPIC_AVAILABLE = False


# ============================================================
# AICoder
# ============================================================
class AICoder:
    """
    Claude API 비동기 클라이언트.

    사용법:
        ai = AICoder()
        ai.generate("파이썬으로 hello world")
        while True:
            result = ai.get_result()
            if result is not None:
                print(result['code'])
                break
            time.sleep(0.05)
    """

    def __init__(self, api_key=None, model=MODEL_NAME):
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._result = None        # 백그라운드 스레드가 결과 채움
        self._lock = threading.Lock()
        self._worker = None
        self._busy = False         # 진행 중 플래그
        self._stub_start_time = None
        self._stub_text = None

        # stub 모드 결정
        if not ANTHROPIC_AVAILABLE:
            self.stub_mode = True
            self._stub_reason = "anthropic 패키지 미설치 (pip install anthropic)"
        elif not self.api_key:
            self.stub_mode = True
            self._stub_reason = "ANTHROPIC_API_KEY 환경변수 미설정"
        else:
            self.stub_mode = False
            self._stub_reason = None
            self.client = Anthropic(api_key=self.api_key)

        if self.stub_mode:
            print(f"[ai_coder] STUB 모드 활성 — {self._stub_reason}")
        else:
            print(f"[ai_coder] Claude API 모드 활성 (model={self.model})")

    # ──────────────────────────────────────────
    # 비동기 생성 시작
    # ──────────────────────────────────────────
    def generate(self, text):
        """비동기 코드 생성 시작. 즉시 반환."""
        if self._busy:
            print("[ai_coder] 이미 진행 중 — 무시됨")
            return
        self._busy = True
        with self._lock:
            self._result = None

        if self.stub_mode:
            # stub: 시간 기록만 해두고 get_result() 에서 처리
            self._stub_text = text
            self._stub_start_time = time.time()
            return

        # 실제 API 호출은 백그라운드 스레드에서
        self._worker = threading.Thread(
            target=self._call_api, args=(text,), daemon=True
        )
        self._worker.start()

    # ──────────────────────────────────────────
    # 결과 폴링
    # ──────────────────────────────────────────
    def get_result(self):
        """
        매 프레임 호출. 결과 있으면 dict, 없으면 None 반환.
        반환 후에는 result 가 비워지므로 한 번만 받을 수 있음.
        """
        # stub 처리: STUB_DELAY_SEC 후 더미 응답
        if self.stub_mode and self._stub_start_time is not None:
            if time.time() - self._stub_start_time >= STUB_DELAY_SEC:
                code = self._stub_response(self._stub_text)
                self._stub_start_time = None
                self._stub_text = None
                self._busy = False
                return {'status': 'ok', 'code': code}
            return None

        # 실제 모드: lock 으로 안전하게 결과 가져오기
        with self._lock:
            if self._result is not None:
                r = self._result
                self._result = None
                self._busy = False
                return r
        return None

    # ──────────────────────────────────────────
    # 내부: 실제 API 호출 (백그라운드 스레드에서 실행)
    # ──────────────────────────────────────────
    def _call_api(self, text):
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": text}
                ]
            )
            # response.content 는 ContentBlock 리스트
            code_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    code_text += block.text
            with self._lock:
                self._result = {'status': 'ok', 'code': code_text.strip()}
        except Exception as e:
            with self._lock:
                self._result = {'status': 'err', 'msg': str(e)}

    # ──────────────────────────────────────────
    # 내부: stub 응답
    # ──────────────────────────────────────────
    def _stub_response(self, text):
        """API 키 없이 동작 확인용 더미 코드 생성."""
        return (
            f"# [STUB 모드 — 실제 AI 호출 안 됨]\n"
            f"# 입력: {text!r}\n"
            f"# (실제 사용 시 ANTHROPIC_API_KEY 환경변수 설정 필요)\n"
            f"\n"
            f"print('Hello from BCI!')\n"
            f"print('받은 명령: {text}')\n"
        )


# ============================================================
# 단독 실행 시 — 간단 테스트
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print(" ai_coder.py 단독 테스트")
    print("=" * 50)
    ai = AICoder()
    print()
    print("생성 시작: '파이썬으로 1부터 10까지 합 출력'")
    ai.generate("파이썬으로 1부터 10까지 합 출력")

    while True:
        result = ai.get_result()
        if result is not None:
            print()
            print("─" * 50)
            print("결과:", result.get('status'))
            print("─" * 50)
            if result.get('status') == 'ok':
                print(result['code'])
            else:
                print(f"오류: {result.get('msg')}")
            break
        time.sleep(0.1)
