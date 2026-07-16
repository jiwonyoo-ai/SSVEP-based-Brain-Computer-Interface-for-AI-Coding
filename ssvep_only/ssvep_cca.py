"""
ssvep_cca.py — CCA 베이스라인 SSVEP 분류기
=================================================================

[CCA란]
  Canonical Correlation Analysis (정준 상관 분석)
  EEG 신호와 각 자극 주파수의 정현파(sin/cos) 사이의
  상관계수를 구해서 가장 높은 주파수를 선택.

[FBCCA와 차이]
  CCA  : 필터뱅크 없이 원신호 그대로 한 번만 상관분석
  FBCCA: 여러 대역으로 나눠서 각각 CCA → 가중합산

[사용법]
  from ssvep_cca import CCA
  clf = CCA(freqs=[9.25, 10.0, 12.0, 15.0], fs=222)
  probs = clf.predict_proba(window)   # window: (1, n_samples)
  scores = clf._compute_scores(window)
"""

import numpy as np


class CCA:
    def __init__(self, freqs, fs, n_harmonics=3):
        """
        Parameters
        ----------
        freqs       : 자극 주파수 목록 (예: [9.25, 10.0, 12.0, 15.0])
        fs          : 샘플링 주파수 (Hz)
        n_harmonics : 사용할 고조파 수 (기본 3 → 기본파+2배+3배)
        """
        self.freqs = freqs
        self.fs = fs
        self.n_harmonics = n_harmonics

    def _make_reference(self, freq, n_samples):
        """
        주파수 freq에 대한 참조 신호 생성
        행: [sin(f), cos(f), sin(2f), cos(2f), sin(3f), cos(3f), ...]
        """
        t = np.arange(n_samples) / self.fs
        refs = []
        for h in range(1, self.n_harmonics + 1):
            refs.append(np.sin(2 * np.pi * h * freq * t))
            refs.append(np.cos(2 * np.pi * h * freq * t))
        return np.array(refs)  # (2*n_harmonics, n_samples)

    def _cca(self, X, Y):
        """
        X: (n_ch, n_samples) — EEG 신호
        Y: (n_ref, n_samples) — 참조 신호

        반환: 첫 번째 정준 상관계수 (스칼라)
        """
        # 평균 제거 (zero-mean)
        X = X - X.mean(axis=1, keepdims=True)
        Y = Y - Y.mean(axis=1, keepdims=True)

        n = X.shape[1]

        # 공분산 행렬
        Cxx = X @ X.T / n   # (n_ch, n_ch)
        Cyy = Y @ Y.T / n   # (n_ref, n_ref)
        Cxy = X @ Y.T / n   # (n_ch, n_ref)

        # 정규화: Cxx^(-1/2) @ Cxy @ Cyy^(-1/2)
        # 수치 안정성을 위해 SVD 사용
        try:
            Ux, Sx, _ = np.linalg.svd(Cxx, full_matrices=False)
            Uy, Sy, _ = np.linalg.svd(Cyy, full_matrices=False)

            # 역제곱근 (작은 값은 0으로)
            eps = 1e-10
            Sx_inv_sqrt = np.diag(1.0 / np.sqrt(np.maximum(Sx, eps)))
            Sy_inv_sqrt = np.diag(1.0 / np.sqrt(np.maximum(Sy, eps)))

            Cxx_inv_sqrt = Ux @ Sx_inv_sqrt @ Ux.T
            Cyy_inv_sqrt = Uy @ Sy_inv_sqrt @ Uy.T

            # 정규화된 교차공분산
            M = Cxx_inv_sqrt @ Cxy @ Cyy_inv_sqrt

            # SVD → 첫 번째 특이값 = 최대 정준 상관계수
            S = np.linalg.svd(M, compute_uv=False)
            return float(S[0])

        except np.linalg.LinAlgError:
            return 0.0

    def _compute_scores(self, window):
        """
        window: (1, n_samples) numpy array
        반환: (n_freqs,) 각 주파수의 CCA 상관계수
        """
        n_samples = window.shape[1]
        scores = []
        for freq in self.freqs:
            ref = self._make_reference(freq, n_samples)
            r = self._cca(window, ref)
            scores.append(r)
        return np.array(scores)

    def predict_proba(self, window):
        """
        window: (1, n_samples) numpy array
        반환: (n_freqs,) softmax 확률
        """
        scores = self._compute_scores(window)
        exp_s = np.exp(scores - np.max(scores))
        return exp_s / exp_s.sum()

    def predict(self, window):
        """가장 높은 확률의 주파수 인덱스 반환"""
        return int(np.argmax(self.predict_proba(window)))