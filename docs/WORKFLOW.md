# 워크플로우 다이어그램 — DX 파이프라인 + MoA 오케스트레이션

> 보고서 삽입용. 실제 구현(v2.8) 기준으로 작성 — 개념도가 아니라 코드와 1:1 대응.
> 렌더링: Obsidian·GitHub에서 Mermaid 자동 렌더링됨.

## 1. 전체 구조 (DX → AX 2단 구조)

```mermaid
flowchart LR
    subgraph DX["DX 파이프라인 (결정론적 코드)"]
        direction TB
        C01["01_collect<br/>플레이스토어 리뷰 수집"] --> C02["02_preprocess<br/>정제 + Kiwi 형태소"]
        C02 --> C03["03_embedding<br/>TF-IDF + Ko-SBERT"]
        C03 --> C05["05_painpoint<br/>감성분석 + BERTopic/LDA"]
        SURV["data/survey.csv<br/>(팀 설문)"] --> C04["04_segmentation<br/>K-Means + PCA"]
        C05 --> C06["06_visualize<br/>우선순위 매트릭스 + 레이더"]
    end

    subgraph GATE["계보 게이트 (lineage.py)"]
        direction TB
        G1["run_id 3자 일치<br/>+ SHA-256 해시 체인 검증"]
        G1 -->|통과| G2["data_mode = real"]
        G1 -->|실패| G3["data_mode = hypothesis<br/>(가설 모드 강등)"]
    end

    subgraph AX["MoA 오케스트레이션 (moa_orchestrator.py)"]
        direction TB
        L1["Layer 1: A·B·C·D 병렬"] --> L2["Layer 2: E·F 통합"]
        L2 --> L3["Layer 3: Master Agent G<br/>(Claude Code)"]
    end

    DX --> GATE --> AX
    L3 --> RPT["CX_분석결과.md<br/>+ 사람 검수 체크리스트"]
```

## 2. MoA 3-Layer 상세 (에이전트별 역할·데이터 신뢰 등급)

```mermaid
flowchart TB
    subgraph L1["Layer 1 — Specialist Agents (GPT, 병렬 호출)"]
        A["A. 시장 조사<br/>(무검색 — 미검증)"]
        B["B. VOC 분석<br/>painpoints.csv 실데이터 주입<br/>지시=system / 데이터=user JSON"]
        C["C. 경쟁 분석<br/>(무검색 — 미검증)"]
        D["D. 트렌드 분석<br/>(무검색 — 미검증)"]
    end

    subgraph L2["Layer 2 — 통합 Agents (GPT)"]
        E["E. 타겟 세그먼트 후보<br/>← A + B"]
        F["F. 시장 기회<br/>← C + D"]
    end

    subgraph L3["Layer 3 — Master Agent (Claude Code = G)"]
        G["교차 검증 · 인용 대조 · 오염 탐지<br/>신뢰도 종합 = (0.4×E + 0.35×B) / 0.75<br/>K-Means 세그먼트로 E 결론 교차 확인"]
    end

    A --> E
    B --> E
    C --> F
    D --> F
    E --> G
    F --> G
    G --> OUT["최종 보고서 (AI 초안 — 최종 책임은 팀)"]
```

## 3. 신뢰 경계 (prompt injection 방어 관점)

```mermaid
flowchart LR
    TRUST["신뢰 영역<br/>DX 산출물 (해시 검증됨)<br/>orchestrator 코드"] -->|"system 지시 / user JSON 데이터 분리"| GPT["비신뢰 영역<br/>GPT A~F 출력 (A.md~F.md)"]
    GPT -->|"외부 리뷰 텍스트 포함 —<br/>지시로 취급 금지"| G2["Master Agent G<br/>인용은 원본 CSV 대조<br/>극단 신뢰도 = 오염 의심"]
    G2 --> HUMAN["사람 검수 체크리스트<br/>(최종 게이트)"]
```

## 보고서 스토리 포인트 (REMEMBER 반영)

1. **AI 결과는 초안** — 계보 게이트가 실데이터 여부를 시스템이 보장, 미검증 수치는 표기 유지
2. **최종 책임은 사람** — Layer 3 뒤에 사람 검수 체크리스트가 항상 마지막 게이트
3. **재사용 자산** — SERVICE·APP_ID·FEATURE_COLUMNS 3개 값만 바꾸면 다른 서비스 분석에 그대로 재사용
