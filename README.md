# PrasiaLab_guild_Trace

프라시아 전기 공개 랭킹 데이터를 기반으로 서버 이동 전후 결사의 유사성을 비교하는 실험용 페이지입니다.

## 화면 파일

- `index.html`
- `css/style.css`
- `js/app.js`
- `data/compare/latest.json`

## 파이썬 스크립트 실행 순서

### 1. 스냅샷 저장

```bash
python scripts/01_collect_snapshot.py --snapshot-id 2026-06-25_1200
```

기본 입력은 `data/Who_are_you_guild_score.json`입니다. 개인/직업 랭킹 JSON이 있으면 다음처럼 추가할 수 있습니다.

```bash
python scripts/01_collect_snapshot.py --snapshot-id 2026-06-25_1200 --member-source data/Who_are_you.json --member-source data/Who_are_you_class.json
```

### 2. 결사 점수 재계산

```bash
python scripts/02_build_guild_score.py --snapshot-id 2026-06-25_1200
```

### 3. 이전/이후 스냅샷 비교

```bash
python scripts/03_build_trace_compare.py --before 2026-06-24_1200 --after 2026-06-25_1200
```

출력은 `data/compare/<이전>__<이후>.json`과 `data/compare/latest.json`으로 생성됩니다.

### 4. 저장된 모든 스냅샷 조합 비교

```bash
python scripts/04_make_all_compares.py
```

## 비교 기준

- 일반 결사원 닉네임은 기본 점수 산정에서 제외합니다.
- 결사장 닉네임은 주요 기준으로 사용합니다.
- 결사명은 변경/선점 가능성이 있으므로 보너스 기준으로만 사용합니다.
- 91레벨 이상 멤버의 레벨 분포, 직업군 분포, 레벨별 직업군 분포를 핵심 기준으로 사용합니다.
- 결사순위 점수는 후보 정렬 및 근접도 보정값으로 사용합니다.

기본 비교는 속도를 위해 이전 상위 200개 결사, 이후 상위 300개 결사를 대상으로 합니다. 전체 비교가 필요하면 `--before-limit 0 --after-limit 0` 옵션을 사용하세요.
