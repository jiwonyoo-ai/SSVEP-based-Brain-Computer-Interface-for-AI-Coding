This project explores how physiological signals can be used as an alternative input modality for AI systems, from EEG signal acquisition and classification to LLM-assisted code generation.

# SSVEP-based Brain-Computer Interface for AI-assisted Programming

EEG 기반 Brain-Computer Interface(BCI)와 LLM을 결합하여, 뇌파로 입력한 제한적인 명령을 자연어로 보정하고 Python 코드 생성까지 연결하는 AI-assisted programming 시스템입니다.

본 프로젝트에서는 **SSVEP 기반 EEG 신호를 실시간으로 수집·분류하고, 이를 LLM 기반 자연어 처리 및 코드 생성으로 연결하는 end-to-end 파이프라인**을 설계·구현했습니다. 또한 실제 사용자를 대상으로 실험을 수행하여 EEG 기반 인터페이스의 활용 가능성을 검증했습니다.

---

# Project Overview

## Motivation

EEG 기반 인터페이스는 주로 의료, 재활, 뉴로피드백 등의 분야에서 활용되어 왔으며, 본 프로젝트에서는 이를 **AI 시스템의 새로운 입력 방식**으로 확장하고자 했습니다.

특히 제한적인 EEG 입력을 생성형 AI와 결합하면, 사용자가 직접 많은 문장을 입력하지 않더라도 AI가 의도를 보완하여 보다 복잡한 작업을 수행할 수 있다고 판단했습니다.

이를 바탕으로 **SSVEP 기반 EEG 입력과 LLM을 결합하여 뇌파만으로 프로그래밍할 수 있는 AI-assisted programming 환경**을 구축했습니다.

---

# Objectives

- SSVEP 기반 실시간 EEG 입력 시스템 구현
- FBCCA 기반 EEG 신호 분류
- 제한적인 EEG 입력을 자연어 명령으로 변환
- LLM 기반 Python 코드 생성
- BCI와 생성형 AI를 결합한 사용자 인터페이스 구현
- 실제 사용자 실험을 통한 시스템 검증

---

# System Architecture

```text
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
````

---

# Workflow

### 1. SSVEP Stimulus

사용자는 서로 다른 주파수(9.25Hz, 10Hz, 12Hz, 15Hz)로 깜빡이는 시각 자극 중 원하는 항목을 응시합니다.

---

### 2. EEG Acquisition

비침습형 EEG 장비를 이용하여 사용자의 EEG 신호를 실시간으로 수집합니다.

---

### 3. Signal Classification

수집된 EEG 신호를 **FBCCA (Filter Bank Canonical Correlation Analysis)**를 이용하여 분석하고, 사용자가 응시한 시각 자극의 주파수를 분류합니다.

성능 비교를 위해 CCA 기반 분류도 함께 수행했습니다.

---

### 4. Sentence Generation

분류된 결과를 기반으로 사용자의 입력 의도를 나타내는 제한적인 문장을 생성합니다.

---

### 5. Prompt Refinement

EEG 입력 과정에서 생성된 짧거나 불완전한 문장을 Claude를 이용하여 자연스러운 프로그래밍 명령으로 보정합니다.

예시:

```text
sort list
```

↓

```text
Write Python code to sort a list in ascending order.
```

---

### 6. AI Code Generation

보정된 자연어 명령을 기반으로 Claude가 Python 코드 후보를 생성합니다.

---

### 7. User Selection

사용자는 생성된 코드 후보 중 원하는 결과를 선택합니다.

---

### 8. Result Storage

EEG 신호, 분류 결과 및 선택 결과를 저장하여 시스템 성능과 사용자 반응을 분석합니다.

---

# Core Technologies

## SSVEP-based Brain-Computer Interface

사용자가 특정 주파수의 시각 자극을 응시할 때 EEG에 나타나는 주파수 특성을 이용하여 사용자의 의도를 입력으로 변환합니다.

---

## FBCCA

**Filter Bank Canonical Correlation Analysis (FBCCA)**를 이용하여 여러 주파수 대역에서 EEG 신호와 기준 신호의 상관관계를 분석하고, 사용자가 응시한 자극 주파수를 분류합니다.

CCA 기반 분류 결과와 비교하여 성능을 평가했습니다.

---

## LLM-assisted Programming

Claude를 활용하여 EEG 기반의 제한적인 입력을 자연어 명령으로 보정하고, 이를 Python 코드 생성으로 연결했습니다.

주요 기능:

* 자연어 명령 보정
* 사용자 의도 확장
* Python 코드 생성
* 생성 결과 선택

---

# Experimental Setup

| Item                 | Description                 |
| -------------------- | --------------------------- |
| EEG                  | Non-invasive EEG            |
| BCI Paradigm         | SSVEP                       |
| Stimulus Frequency   | 9.25Hz / 10Hz / 12Hz / 15Hz |
| Classifier           | FBCCA, CCA                  |
| AI Model             | Claude                      |
| Programming Language | Python                      |
| Participants         | 13                          |

---

# Performance Optimization

실제 EEG 신호에서는 FBCCA Score가 작은 값을 가지면서 noise와 실제 SSVEP 신호를 구분하기 어려운 문제가 발생했습니다.

4-Class Softmax를 적용했을 때 실제 신호에서도 약 0.30 수준의 Confidence가 나타났으며, 기존 Threshold인 0.6에서는 실제 신호까지 제외되는 문제가 발생했습니다.

Threshold를 0.27까지 낮추자 실제 신호의 통과율은 증가했지만, 랜덤 노이즈 역시 약 0.25 수준의 Confidence를 보여 False Positive가 증가했습니다.

이를 해결하기 위해 **Softmax Confidence와 원본 FBCCA Score Ratio를 함께 사용하는 이중 조건**을 적용했습니다.

```text
Softmax Confidence ≥ 0.27

AND

Original FBCCA Score Ratio ≥ 2.5
```

Softmax Confidence를 통해 최소 신뢰도를 확인하고, FBCCA Score Ratio를 통해 가장 높은 Score가 두 번째 Score보다 충분히 높은 경우에만 입력을 허용하도록 설계했습니다.

---

# Results

* FBCCA와 CCA의 분류 성능 비교
* 동일 Threshold 기준 약 75% 높은 통과율 확인
* ITR 약 7.2배 향상
* 실제 사용자 실험을 통한 시스템 검증
* 사용자 피드백을 기반으로 UI 개선 방향 도출

---

# My Contributions

* 프로젝트 기획 및 시스템 아키텍처 설계
* SSVEP 및 EEG 관련 논문 조사
* EEG 기반 사용자 인터페이스 설계 및 구현
* FBCCA 및 CCA 기반 EEG 신호 분석
* EEG 분류 성능 비교 및 threshold optimization
* LLM-assisted Programming 파이프라인 구현
* 사용자 실험 설계 및 결과 분석


