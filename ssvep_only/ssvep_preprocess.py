"""
ssvep_preprocess.py — SSVEP 전용 전처리 파이프라인
=================================================================
[변경 사항]
  - P300 전처리 완전 제거
  - SSVEP epoch만 추출 + 저장
  - subject ID 기반 자동 파일 감지

[파이프라인]
  ① Load + timestamp 보간
  ② Burst 제거 + 채널 sanity check
  ③ 대역통과 필터 (6~25 Hz) + 노치 (60 Hz)
  ④ SSVEP epoch 추출 (SSVEP_START 기준 0.2~4.0초)
  ⑤ Detrend (DC + linear trend 제거)
  ⑥ Artifact rejection
  ⑦ 저장 + PSD 시각화

[출력]
  recordings/sub{ID}/preprocessed/preprocessed_ssvep.npz

[사용법]
  python ssvep_preprocess.py A          # subA 최신 파일 자동 감지
  python ssvep_preprocess.py 01         # sub01 최신 파일 자동 감지
  python ssvep_preprocess.py A eeg.csv events.csv  # 직접 지정
"""

import os
import sys
import glob
import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt, iirnotch, detrend, welch
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# ============================================================
# 설정
# ============================================================
class Config:
    BURST_SKIP_SEC  = 0.5
    NOTCH_FREQ      = 60.0
    NOTCH_Q         = 30.0
    SSVEP_BP        = (6.0, 25.0)
    FILTER_ORDER    = 4
    SSVEP_EFFECTIVE = (0.2, 4.0)   # SSVEP_START 기준
    AMP_THRESHOLD   = 150.0
    GRAD_THRESHOLD  = 75.0
    REJECT_WARN     = 0.05
    STIM_FREQS      = [9.25, 10.0, 12.0, 15.0]
    RECORDINGS_DIR  = "recordings"


# ============================================================
# 유틸
# ============================================================
def _parse_ts(s):
    try:
        return datetime.strptime(s.strip(), '%Y %m %d %H:%M:%S.%f').timestamp()
    except Exception:
        return None


def load_eeg(path):
    df   = pd.read_csv(path, encoding='utf-8')
    cols = [c for c in df.columns if c.lower() != "time"]
    data = df[cols].apply(pd.to_numeric, errors="coerce").values.astype(float)
    if np.any(np.isnan(data)):
        data = pd.DataFrame(data).ffill().bfill().values

    time_col = df["time"].astype(str)
    ts_mask  = time_col.str.len() > 5
    ts_idx   = df.index[ts_mask].to_numpy()
    ts_unix  = np.array([_parse_ts(time_col.iloc[i]) for i in ts_idx])
    valid    = np.array([v is not None for v in ts_unix])
    ts_idx   = ts_idx[valid]
    ts_unix  = ts_unix[valid].astype(float)

    N        = len(df)
    sample_t = np.zeros(N)
    for k in range(len(ts_idx) - 1):
        i0, i1 = ts_idx[k], ts_idx[k+1]
        t0, t1 = ts_unix[k], ts_unix[k+1]
        sample_t[i0:i1] = np.linspace(t0, t1, i1-i0, endpoint=False)
    last = ts_idx[-1]
    dur  = ts_unix[-1] - ts_unix[0]
    dt   = 1.0 / (N / dur)
    sample_t[last:] = ts_unix[-1] + np.arange(N - last) * dt
    fs = N / dur
    return sample_t, data, cols, float(fs)


def trim_burst(t, data):
    cutoff = t[0] + Config.BURST_SKIP_SEC
    keep   = t >= cutoff
    return t[keep], data[keep]


def channel_sanity(data, names):
    print("  채널 통계:")
    for i, name in enumerate(names):
        ch = data[:, i]
        print(f"    {name}: mean={ch.mean():.1f}  std={ch.std():.1f}  "
              f"range=[{ch.min():.0f}, {ch.max():.0f}]")
        if ch.std() < 1.0:
            print(f"    ⚠️  {name} 거의 평탄 — 전극 확인")


def apply_filter(data, fs):
    b_notch, a_notch = iirnotch(Config.NOTCH_FREQ, Config.NOTCH_Q, fs)
    b_bp, a_bp = butter(Config.FILTER_ORDER,
                        [Config.SSVEP_BP[0]/(fs/2), Config.SSVEP_BP[1]/(fs/2)],
                        btype='band')
    out = np.zeros_like(data)
    for i in range(data.shape[1]):
        x = data[:, i] - data[:, i].mean()
        x = filtfilt(*[b_bp, a_bp], x)
        x = filtfilt(*[b_notch, a_notch], x)
        out[:, i] = x
    return out


def load_events(path):
    ev = pd.read_csv(path, encoding='utf-8')
    ev["t_unix"] = ev["timestamp"].apply(_parse_ts).astype(float)
    return ev


def extract_ssvep(t, data_filt, events, win=Config.SSVEP_EFFECTIVE):
    starts = events[events.event == "SSVEP_START"].reset_index(drop=True)
    epochs, labels = [], []
    for _, row in starts.iterrows():
        t0 = row["t_unix"] + win[0]
        t1 = row["t_unix"] + win[1]
        i0, i1 = np.searchsorted(t, t0), np.searchsorted(t, t1)
        seg = data_filt[i0:i1, :]
        if len(seg) > 0:
            epochs.append(seg)
            labels.append(int(row["target_quadrant"]))
    if not epochs:
        raise ValueError("SSVEP epoch이 하나도 없어요. 이벤트 파일 확인하세요.")
    n_min = min(e.shape[0] for e in epochs)
    X = np.array([e[:n_min] for e in epochs]).transpose(0, 2, 1)
    return X, np.array(labels)


def reject_artifacts(X, name="SSVEP"):
    amp  = np.max(np.abs(X), axis=(1, 2))
    grad = np.max(np.abs(np.diff(X, axis=2)), axis=(1, 2))
    keep  = (amp <= Config.AMP_THRESHOLD) & (grad <= Config.GRAD_THRESHOLD)
    n_rej = (~keep).sum()
    ratio = n_rej / len(X) if len(X) else 0
    flag  = " ⚠️" if ratio > Config.REJECT_WARN else ""
    print(f"  {name}: {n_rej}/{len(X)} rejected ({ratio*100:.1f}%){flag}")
    return keep


def psd_viz(X, y, fs, ch_names, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    fig, axes = plt.subplots(4, 1, figsize=(10, 10), sharex=True)
    for q in range(4):
        ax  = axes[q]
        sel = (y == q)
        if sel.sum() == 0:
            ax.set_title(f"Q{q} — 없음"); continue
        nperseg = min(int(fs * 2), X.shape[2])
        psds = []
        for ep in X[sel, 0]:
            f, P = welch(ep, fs=fs, nperseg=nperseg)
            psds.append(P)
        psd = np.mean(psds, axis=0)
        ax.semilogy(f, psd, color='k')
        for fi, f0 in enumerate(Config.STIM_FREQS):
            ax.axvline(f0, color='red' if fi == q else 'gray',
                       lw=1.5, alpha=0.7, label=f"{f0}Hz")
        ax.set_xlim(1, 30)
        ax.set_title(f"Q{q} 타겟 (n={sel.sum()})")
        ax.legend(fontsize=8, ncol=4); ax.grid(alpha=0.3)
    axes[-1].set_xlabel("Frequency (Hz)")
    plt.suptitle("SSVEP PSD — 분면별")
    plt.tight_layout()
    path = os.path.join(output_dir, "ssvep_psd.png")
    plt.savefig(path, dpi=120, bbox_inches='tight')
    plt.close()
    print(f"  → {path}")


# ============================================================
# 자동 파일 감지
# ============================================================
def find_latest(sid, recordings_dir=Config.RECORDINGS_DIR):
    sub_dir = os.path.join(recordings_dir, f"sub{sid}")
    if not os.path.isdir(sub_dir):
        available = sorted(glob.glob(os.path.join(recordings_dir, "sub*")))
        raise FileNotFoundError(
            f"sub{sid} 폴더 없음\n  사용 가능: "
            + (", ".join(os.path.basename(d) for d in available) or "(없음)")
        )
    eeg_files = sorted([f for f in glob.glob(os.path.join(sub_dir, "*.csv"))
                        if "_events" not in f])
    evt_files = sorted(glob.glob(os.path.join(sub_dir, "*_events.csv")))
    if not eeg_files or not evt_files:
        raise FileNotFoundError(f"CSV 파일 없음: {sub_dir}")
    return eeg_files[-1], evt_files[-1]


# ============================================================
# 메인
# ============================================================
def run(eeg_csv, events_csv, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    print("="*55); print(" ① Load + timestamp 보간"); print("="*55)
    t, data, ch_names, fs = load_eeg(eeg_csv)
    print(f"  채널: {ch_names},  fs ≈ {fs:.1f} Hz,  샘플: {len(data)}")

    print("\n"+"="*55); print(" ② Burst 제거 + sanity"); print("="*55)
    t, data = trim_burst(t, data)
    channel_sanity(data, ch_names)

    print("\n"+"="*55); print(" ③ 필터 적용"); print("="*55)
    data_filt = apply_filter(data, fs)
    print(f"  SSVEP BP {Config.SSVEP_BP} Hz + Notch {Config.NOTCH_FREQ} Hz 완료")

    print("\n"+"="*55); print(" ④ SSVEP epoch 추출"); print("="*55)
    events = load_events(events_csv)
    X, y   = extract_ssvep(t, data_filt, events)
    print(f"  X: {X.shape},  분포: {np.bincount(y)}")

    print("\n"+"="*55); print(" ⑤ Detrend"); print("="*55)
    from scipy.signal import detrend as sp_detrend
    X = sp_detrend(X, axis=2)
    print("  DC + linear trend 제거 완료")

    print("\n"+"="*55); print(" ⑥ Artifact rejection"); print("="*55)
    keep = reject_artifacts(X)
    X, y = X[keep], y[keep]
    print(f"  최종: X{X.shape},  분포: {np.bincount(y)}")

    print("\n"+"="*55); print(" ⑦ 저장 + PSD"); print("="*55)
    save_path = os.path.join(output_dir, "preprocessed_ssvep.npz")
    np.savez(save_path,
             X=X, y_quad=y, fs=fs,
             channels=np.array(ch_names, dtype=object),
             stim_freqs=np.array(Config.STIM_FREQS),
             ssvep_window=np.array(Config.SSVEP_EFFECTIVE))
    print(f"  → {save_path}")
    psd_viz(X, y, fs, ch_names, output_dir)

    print("\n 전처리 완료!")
    return X, y, fs


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("사용법:")
        print("  python ssvep_preprocess.py A")
        print("  python ssvep_preprocess.py 01")
        sys.exit(1)

    sid  = args[0]
    if len(args) >= 3:
        eeg_csv, events_csv = args[1], args[2]
        output_dir = os.path.join(Config.RECORDINGS_DIR, f"sub{sid}", "preprocessed")
    else:
        try:
            eeg_csv, events_csv = find_latest(sid)
            output_dir = os.path.join(Config.RECORDINGS_DIR, f"sub{sid}", "preprocessed")
        except FileNotFoundError as e:
            print(f"\n[ERROR] {e}"); sys.exit(1)

    print(f"\n  Subject : sub{sid}")
    print(f"  EEG     : {eeg_csv}")
    print(f"  Events  : {events_csv}")
    print(f"  Output  : {output_dir}\n")
    run(eeg_csv, events_csv, output_dir)
