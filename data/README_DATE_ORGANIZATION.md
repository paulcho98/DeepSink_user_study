# 📁 날짜별 폴더 구조 시스템

## 개요
사용자 연구 분석 시스템의 모든 출력 결과가 날짜별로 정리된 폴더 구조를 사용합니다.

## 📂 폴더 구조

```
InterGenEval_user_study/data/
├── analysis_output/           # 데이터 수집 결과
│   └── YYYY-MM-DD/           # 날짜별 폴더
│       └── collection_HHMMSS/ # 수집 시간별 폴더
├── visualization_output/      # 시각화 결과  
│   └── YYYY-MM-DD/           # 날짜별 폴더
│       └── analysis_HHMMSS/   # 분석 시간별 폴더
└── github_analysis_output/    # GitHub 분석 결과
    └── YYYY-MM-DD/           # 날짜별 폴더
        └── github_analysis_HHMMSS/ # GitHub 분석 시간별 폴더
```

## 🎯 적용된 스크립트들

### 1. 데이터 수집 스크립트
- **`collect_simple_fixed.py`**: GitHub Issues에서 사용자 연구 결과 수집
  - 출력: `analysis_output/YYYY-MM-DD/collection_HHMMSS/`
  - 파일: `collected_results.json`, `analysis_report.txt`

- **`collect_github_results_no_viz.py`**: GitHub 결과 수집 (시각화 없음)  
  - 출력: `github_analysis_output/YYYY-MM-DD/github_analysis_HHMMSS/`
  - 파일: `raw_results.json`, `analysis_summary.json`, `model_comparison_summary.csv`

### 2. 분석 및 집계 스크립트
- **`aggregate_results_new.py`**: 사용자 응답 데이터 집계 및 분석
  - 출력: `analysis_output/YYYY-MM-DD/aggregation_HHMMSS/`
  - 파일: `aggregated_results.txt`, `detailed_results.json`, `all_responses.csv`

### 3. 시각화 스크립트  
- **`visualize_user_study.py`**: 종합 시각화 생성
  - 출력: `visualization_output/YYYY-MM-DD/analysis_HHMMSS/`
  - 파일: 각종 차트 PNG, CSV 데이터, 리포트, 메타데이터

## 📋 출력 파일 설명

### analysis_output (데이터 수집)
- `collected_results.json`: 원시 사용자 응답 데이터
- `analysis_report.txt`: 수집 요약 리포트

### visualization_output (시각화)
- `win_rates_heatmap.png`: 승률 히트맵
- `overall_ranking.png`: 전체 순위 차트  
- `comparison_matrix.png`: 모델 비교 매트릭스
- `detailed_stats.png`: 상세 통계 차트
- `individual_radar_charts.png`: 개별 모델 레이더 차트
- `combined_radar_chart.png`: 통합 레이더 차트
- `summary_report.txt`: 분석 요약 리포트
- `README.md`: 분석 결과 설명
- `analysis_metadata.json`: 분석 메타데이터

### github_analysis_output (GitHub 분석)
- `raw_results.json`: GitHub에서 수집한 원시 데이터
- `analysis_summary.json`: 분석 요약
- `model_comparison_summary.csv`: 모델 비교 요약 CSV

## 🚀 사용 방법

### 데이터 수집
```bash
# GitHub에서 사용자 연구 결과 수집
python collect_simple_fixed.py

# 출력: analysis_output/2025-09-24/collection_143129/
```

### 시각화 생성
```bash
# 수집된 데이터로 시각화 생성
python visualize_user_study.py analysis_output/2025-09-24/collection_143129/collected_results.json

# 출력: visualization_output/2025-09-24/analysis_143500/
```

### GitHub 분석
```bash  
# GitHub Issues 기반 분석
python collect_github_results_no_viz.py

# 출력: github_analysis_output/2025-09-24/github_analysis_143000/
```

## 🔄 이전 버전과의 호환성

기존 타임스탬프 기반 파일명 시스템에서 날짜별 폴더 구조로 변경되었습니다:

**이전**: `collected_results_fixed_20250924_141630.json`  
**현재**: `analysis_output/2025-09-24/collection_143129/collected_results.json`

## 📈 장점

1. **정리된 구조**: 날짜별로 결과가 체계적으로 정리됨
2. **쉬운 탐색**: 특정 날짜의 분석 결과를 빠르게 찾기 가능
3. **메타데이터 포함**: 각 분석의 상세 정보가 메타데이터로 저장됨
4. **확장 가능**: 새로운 분석 타입 추가 시 동일한 구조 사용 가능

## 🗓️ 예제

2025년 9월 24일에 실행한 분석 결과:

```
data/
├── analysis_output/2025-09-24/collection_143129/
│   ├── collected_results.json
│   └── analysis_report.txt
└── visualization_output/2025-09-24/analysis_143500/
    ├── win_rates_heatmap.png
    ├── combined_radar_chart.png
    ├── summary_report.txt
    └── README.md
```