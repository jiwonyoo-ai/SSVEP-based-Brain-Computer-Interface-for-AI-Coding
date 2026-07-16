"""
ssvep_fbcca.py — Standard CCA + FB-CCA SSVEP 분류기
=================================================================
[구조]
  StandardCCA  : baseline 비교용 (사인/코사인 참조 신호 기반)
  FBCCA        : 메인 온라인 디코더 (Filter Bank + 배음 활용)

[논문 근거]
  - Nakanishi et al. (2015) — CCA 변형 비교
  - Chen et al. (2015)      — Filter Bank CCA

[사용법]
  from ssvep_fbcca import FBCCA, StandardCCA

  clf = FBCCA(freqs=[9.25, 10.0, 12.0, 15.0], fs=222)
  quad  = clf.predict(window)        # (n_ch, n_samp) → int
  probs = clf.predict_proba(window)  # (4,) 확률
"""

import numpy as np
from scipy.signal import butter, filtfilt


# ============================================================
# 공통 설정
# ============================================================
FREQS       = [9.25, 10.0, 12.0, 15.0]
N_HARMONICS = 3
FS          = 222

FILTER_BANKS = [
    (6.0,  90.0),
    (14.0, 90.0),
    (22.0, 90.0),
    (30.0, 90.0),
    (38.0, 90.0),
]
WEIGHTS = np.array([(n + 1) ** (-1.25) + 0.25
                    for n in range(len(FILTER_BANKS))])


# ============================================================
# 공통 유틸
# ============================================================
def _make_ref_signal(freq, n_samp, fs, n_harmonics):
    t = np.arange(n_samp) / fs
    refs = []
    for h in range(1, n_harmonics + 1):
        refs.append(np.sin(2 * np.pi * h * freq * t))
        refs.append(np.cos(2 * np.pi * h * freq * t))
    return np.array(refs)


def _inv_sqrt(C):
    eigval, eigvec = np.linalg.eigh(C)
    eigval = np.maximum(eigval, 1e-10)
    return eigvec @ np.diag(1.0 / np.sqrt(eigval)) @ eigvec.T


def _cca(X, Y):
    """표준 CCA — 최대 상관계수 반환"""
    X = X - X.mean(axis=1, keepdims=True)
    Y = Y - Y.mean(axis=1, keepdims=True)
    # 정규화 — DC 스케일이 크면 공분산 계산이 망가지므로 std로 나눔
    X_std = X.std(axis=1, keepdims=True)
    Y_std = Y.std(axis=1, keepdims=True)
    X_std[X_std < 1e-10] = 1.0
    Y_std[Y_std < 1e-10] = 1.0
    X = X / X_std
    Y = Y / Y_std
    n = X.shape[1]
    Cxx = X @ X.T / n
    Cyy = Y @ Y.T / n
    Cxy = X @ Y.T / n
    try:
        M = _inv_sqrt(Cxx) @ Cxy @ _inv_sqrt(Cyy)
        _, s, _ = np.linalg.svd(M)
        return float(s[0])
    except Exception:
        return 0.0


def _bandpass(data, low, high, fs, order=4):
    nyq   = fs / 2.0
    low_n = max(low  / nyq, 0.01)
    high_n = min(high / nyq, 0.99)
    b, a = butter(order, [low_n, high_n], btype='band')
    out  = np.zeros_like(data)
    for i in range(data.shape[0]):
        out[i] = filtfilt(b, a, data[i])
    return out


def _softmax(x):
    x = x - x.max()
    e = np.exp(x)
    return e / e.sum()


# ============================================================
# Standard CCA — baseline 비교용
# ============================================================
class StandardCCA:
    """
    표준 CCA 분류기 (baseline)
    사인/코사인 참조 신호와 입력 신호의 상관관계로 분류.
    학습 데이터 불필요.
    """

    def __init__(self, freqs=FREQS, fs=FS, n_harmonics=N_HARMONICS):
        self.freqs       = freqs
        self.fs          = fs
        self.n_harmonics = n_harmonics

    def _compute_scores(self, window):
        n_samp = window.shape[1]
        scores = np.zeros(len(self.freqs))
        for fi, freq in enumerate(self.freqs):
            ref = _make_ref_signal(freq, n_samp, self.fs, self.n_harmonics)
            scores[fi] = _cca(window, ref)
        return scores

    def predict(self, window):
        return int(np.argmax(self._compute_scores(window)))

    def predict_proba(self, window):
        return _softmax(self._compute_scores(window))


# ============================================================
# FB-CCA — 메인 온라인 디코더
# ============================================================
class FBCCA:
    """
    Filter Bank CCA 분류기 (메인)
    여러 대역통과 필터로 기본 주파수 + 배음 성분 동시 활용.
    학습 데이터 불필요.
    StandardCCA 대비 짧은 윈도우에서도 안정적.
    """

    def __init__(self, freqs=FREQS, fs=FS,
                 n_harmonics=N_HARMONICS,
                 filter_banks=FILTER_BANKS,
                 weights=WEIGHTS):
        self.freqs        = freqs
        self.fs           = fs
        self.n_harmonics  = n_harmonics
        self.filter_banks = filter_banks
        self.weights      = weights

    def _compute_scores(self, window):
        n_samp = window.shape[1]
        scores = np.zeros(len(self.freqs))
        for fi, freq in enumerate(self.freqs):
            ref      = _make_ref_signal(freq, n_samp, self.fs, self.n_harmonics)
            fb_score = 0.0
            for bi, (low, high) in enumerate(self.filter_banks):
                filtered = _bandpass(window, low, high, self.fs)
                r        = _cca(filtered, ref)
                fb_score += self.weights[bi] * (r ** 2)
            scores[fi] = fb_score
        return scores

    def predict(self, window):
        return int(np.argmax(self._compute_scores(window)))

    def predict_proba(self, window):
        return _softmax(self._compute_scores(window))
