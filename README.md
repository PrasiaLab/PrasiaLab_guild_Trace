# PrasiaLab_guild_Trace

프라시아 전기 공개 랭킹 데이터를 기반으로 서버 이동 전/후 결사의 유사성을 비교하는 실험용 페이지입니다.

## 페이지명

- 추적 연구소
- 서버 이동 전후 결사 유사성 분석

## 핵심 기준

- 일반 결사원 닉네임은 비교 기준에서 제외
- 결사장 닉네임은 주요 기준으로 사용
- 결사명은 필수 조건이 아닌 보너스 기준으로 사용
- 91레벨 이상 멤버의 레벨/직업군 분포를 핵심 지문으로 사용
- 기존 결사순위 점수는 후보 정렬 및 보정값으로 사용

## 고정 결과 경로

```text
data/compare/latest.json
```

나중에 꼬꼬 페이지에 붙일 때는 이 파일만 fetch해서 결과를 표시하면 됩니다.

## 1차 실행

GitHub Pages에 업로드하면 정적 페이지로 동작합니다.
처음에는 `data/compare/latest.json`에 샘플 데이터가 들어 있습니다.

## 비교 스크립트 초안

```bash
python scripts/compare_guilds.py \
  --before data/snapshots/2026-06-24_1800/guilds.json \
  --after data/snapshots/2026-06-25_1200/guilds.json \
  --out data/compare/latest.json
```
