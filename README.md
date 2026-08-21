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
