An SSVEP-based Brain-Computer Interface that enables hands-free AI-assisted coding using EEG signals.

# SSVEP-based Brain-Computer Interface for AI-assisted Programming

EEG 기반 Brain-Computer Interface(BCI)와 LLM을 결합하여, 뇌파로 입력한 제한적인 명령을 자연어로 보정하고 Python 코드 생성까지 연결하는 AI-assisted programming 시스템입니다

본 프로젝트는 SSVEP 기반 EEG 입력, FBCCA 분류 알고리즘, 생성형 AI(Claude)를 하나의 파이프라인으로 통합하여 사용자가 뇌파만으로 코드를 생성할 수 있는 환경을 구현하는 것을 목표로 하였습니다.

기존 EEG 연구가 의료, 재활, 메타버스 분야에 집중되어 있는 것과 달리, 본 프로젝트는 생산성 도구로서의 BCI 활용 가능성을 제시합니다.

---

# Project Overview

## Motivation

현재 EEG 기반 서비스는 의료, 심리 분석, 뉴로피드백, 메타버스 등 다양한 분야에서 활용되고 있지만, 실제 소프트웨어 개발과 같은 생산성 향상을 위한 인터페이스는 거의 연구되지 않았습니다.

또한 신체 활동이 제한된 사용자는 기존 키보드 중심의 개발 환경을 이용하기 어렵다는 한계가 있습니다.

본 프로젝트는 이러한 문제를 해결하기 위해 EEG를 새로운 입력 장치로 활용하여 누구나 뇌파만으로 프로그래밍할 수 있는 환경을 구축하는 것을 목표로 합니다.

---

# Objectives

- SSVEP 기반 실시간 EEG 입력 시스템 구현
- FBCCA 기반 주파수 분류
- 생성형 AI 기반 Python 코드 생성
- 키보드 없는 AI Coding 환경 구축
- BCI와 생성형 AI의 융합 가능성 검증

---

# System Architecture

```
SSVEP Stimulus

        ↓

EEG Acquisition

        ↓

Signal Preprocessing

        ↓

FBCCA Classification

        ↓

Sentence Generation

        ↓

Claude Prompt Refinement

        ↓

Python Code Generation

        ↓

User Selection

        ↓

Result Storage
```

---

# Workflow

### 1. SSVEP Stimulus

사용자는 서로 다른 주파수(9.25Hz, 10Hz, 12Hz, 15Hz)로 깜빡이는 자극 패널 중 원하는 항목을 응시합니다.

---

### 2. EEG Acquisition

비침습형 EEG 장비를 이용하여 사용자의 뇌파를 실시간으로 수집합니다.

---

### 3. Signal Classification

수집된 EEG 신호를 FBCCA(Filter Bank Canonical Correlation Analysis) 알고리즘으로 분석하여 사용자가 바라본 주파수를 분류합니다.

성능 비교를 위해 CCA 알고리즘도 함께 적용하였습니다.

---

### 4. Sentence Generation

분류된 결과를 이용하여 사용자가 입력하고자 하는 문장을 생성합니다.

---

### 5. Prompt Refinement

EEG 입력 과정에서 발생하는 짧거나 부정확한 문장을 Claude를 이용하여 자연스러운 명령문으로 보정합니다.

예시

```
sort list
```

↓

```
Write Python code to sort a list in ascending order.
```

---

### 6. AI Code Generation

보정된 문장을 기반으로 Claude가 Python 코드 후보 2개를 생성합니다.

---

### 7. User Selection

사용자는 생성된 코드 중 원하는 결과를 선택합니다.

---

### 8. Result Storage

선택 결과와 EEG 데이터는 저장되며 시스템 성능 평가 및 분석에 활용됩니다.

---

# Core Technologies

## SSVEP-based Brain Computer Interface

사용자가 특정 주파수의 시각 자극을 응시하면 동일한 주파수 성분이 EEG에서 발생하는 SSVEP 특성을 이용하여 입력을 수행합니다.

---

## FBCCA

Filter Bank Canonical Correlation Analysis(FBCCA)는 여러 주파수 대역에서 EEG와 기준 신호의 상관관계를 계산하여 가장 높은 상관관계를 가지는 주파수를 선택하는 SSVEP 분류 알고리즘입니다.

기존 CCA보다 노이즈에 강하며 더 높은 분류 성능을 제공합니다.

---

## Claude

생성형 AI를 이용하여

- 자연어 문장 보정
- Python 코드 생성

기능을 수행하였습니다.

---

# Experimental Setup

| Item | Description |
|------|-------------|
| EEG | Non-invasive EEG |
| BCI Paradigm | SSVEP |
| Stimulus Frequency | 9.25Hz / 10Hz / 12Hz / 15Hz |
| Classifier | FBCCA, CCA |
| AI Model | Claude |
| Programming Language | Python |

---

# Performance Optimization

실제 EEG에서는 FBCCA Score가 매우 작은 값을 가지는 문제가 발생하였습니다.

4-Class Softmax를 적용하면 실제 신호 역시 약 0.30 수준의 Confidence만 출력되었으며, 기존 Threshold인 0.6은 실제 신호도 통과하지 못했습니다.

Threshold를 0.27까지 낮추었지만 랜덤 노이즈 역시 약 0.25 수준의 Confidence를 가지므로 False Positive가 증가하는 문제가 발생했습니다.

이를 해결하기 위해 다음과 같은 이중 조건을 적용하였습니다.

```
Softmax Confidence ≥ 0.27

AND

Original FBCCA Score Ratio ≥ 2.5
```

Softmax Confidence는 신호의 최소 신뢰도를 확인하고,

원본 FBCCA Score Ratio는 가장 높은 Score와 두 번째 Score의 차이를 비교하여 실제 SSVEP 신호만 선택하도록 하였습니다.

---

# Results

- FBCCA가 CCA보다 높은 분류 성능 확인
- 동일 Threshold 기준 약 75% 높은 통과율
- ITR 약 7.2배 향상
- 사용자 피드백을 통한 UI 개선 방향 도출

---

# My Contributions

- 프로젝트 기획 및 시스템 설계
- 관련 논문 조사 및 SSVEP 알고리즘 분석
- EEG 기반 사용자 인터페이스 설계 및 구현
- FBCCA 및 CCA 성능 비교 및 EEG 신호 분석
- AI-assisted Programming 파이프라인 구현
- 사용자 실험 설계 및 결과 분석

---

# Future Work

- 자유 문장 입력 지원
- 다양한 생성형 AI 모델 비교
- EEG 분류 정확도 향상
- 사용자 인터페이스 개선
- 실시간 AI Coding 환경 고도화
