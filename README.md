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


## 통합 실행

기본적으로는 `scripts/run_trace.py` 하나만 실행하면 됩니다.

```bash
python scripts/run_trace.py --snapshot-id 2026-06-25_1200
```

이전 스냅샷을 직접 지정해 비교하려면 아래처럼 실행합니다.

```bash
python scripts/run_trace.py --snapshot-id 2026-06-25_1200 --before 2026-06-24_1800
```

이미 저장된 스냅샷끼리 비교만 다시 만들고 싶을 때는 아래처럼 실행합니다.

```bash
python scripts/run_trace.py --compare-only --before 2026-06-24_1800 --after 2026-06-25_1200
```

처음 이동 전 데이터만 저장하고 비교는 하지 않을 때는 아래처럼 실행합니다.

```bash
python scripts/run_trace.py --snapshot-id 2026-06-25_1150 --no-compare
```

기존의 `01_collect_snapshot.py`, `02_build_guild_score.py`, `03_build_trace_compare.py`는 세부 작업용으로 남겨둔 파일입니다. 일반 운영에서는 `run_trace.py`만 사용하면 됩니다.

## GitHub Actions 자동/수동 갱신

이 레포에는 `.github/workflows/update_trace.yml`이 포함되어 있습니다.
GitHub에서 `Actions → Update Guild Trace → Run workflow`를 눌러 수동 갱신할 수 있습니다.

입력값:

- `snapshot_id`: 이번에 저장할 스냅샷 ID. 비우면 현재 시간으로 자동 생성됩니다.
- `before`: 비교할 이전 스냅샷 ID. 비우면 저장된 스냅샷 중 직전 데이터를 자동 선택합니다.
- `guild_source`: 결사 랭킹 원본 JSON 경로. 기본값은 `data/Who_are_you_guild_score.json`입니다.
- `no_compare`: `true`로 입력하면 스냅샷 저장만 하고 비교 결과 생성은 건너뜁니다.

낮 12시 이전 데이터는 `no_compare=true`로 먼저 저장하고, 이전 이후에는 `no_compare=false`로 실행하면 직전 스냅샷과 자동 비교됩니다.
