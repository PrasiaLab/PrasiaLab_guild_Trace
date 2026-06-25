# PrasiaLab_guild_Trace

프라시아 전기 공개 랭킹 데이터를 기반으로 서버 이동 전후 결사의 유사성을 비교하는 실험용 페이지입니다.

## 화면 파일

- `index.html`
- `css/style.css`
- `js/app.js`
- `data/compare/latest.json`

## 일반 운영: 한 번에 실행

이 버전부터는 `run_trace.py`가 기본으로 원천 랭킹 데이터 추출까지 먼저 실행합니다.

```bash
python scripts/run_trace.py --snapshot-id 2026-06-25_1150 --no-compare
```

위 명령은 다음을 한 번에 처리합니다.

1. 전체 랭킹 추출 → `data/Who_are_you.json`
2. 결사 랭킹 추출 → `data/Who_are_you_guild.json`
3. 직업별 랭킹 추출 → `data/Who_are_you_class.json`
4. 결사 점수 생성 → `data/Who_are_you_guild_score.json`
5. 스냅샷 저장 → `data/snapshots/<snapshot_id>/guilds.json`
6. 결사 점수 재계산
7. 비교 가능 시 `data/compare/latest.json` 생성

이전 스냅샷과 비교까지 하려면:

```bash
python scripts/run_trace.py --snapshot-id 2026-06-25_1210 --before 2026-06-25_1150
```

기존 JSON만 다시 가공하고 싶을 때는 API 추출을 건너뜁니다.

```bash
python scripts/run_trace.py --snapshot-id 2026-06-25_1210 --use-existing
```

이미 저장된 스냅샷끼리 비교만 다시 만들 때는:

```bash
python scripts/run_trace.py --compare-only --before 2026-06-25_1150 --after 2026-06-25_1210
```

## 포함된 파이썬 스크립트

- `scripts/00_fetch_rankings.py`  
  전체/결사/직업별 랭킹을 API에서 추출하고 `Who_are_you*.json` 파일을 생성합니다.

- `scripts/01_collect_snapshot.py`  
  추출된 JSON을 기준으로 스냅샷을 저장합니다.

- `scripts/02_build_guild_score.py`  
  스냅샷 기준 결사 점수를 재계산합니다.

- `scripts/03_build_trace_compare.py`  
  이전/이후 스냅샷을 비교해 추적 연구소용 결과를 생성합니다.

- `scripts/run_trace.py`  
  위 작업을 원클릭으로 실행하는 통합 실행기입니다.

## GitHub Actions 갱신

`.github/workflows/update_trace.yml`이 포함되어 있습니다.

GitHub에서:

```text
Actions → Update Guild Trace → Run workflow
```

를 눌러 수동 갱신할 수 있습니다.

입력값:

- `snapshot_id`: 이번에 저장할 스냅샷 ID. 비우면 현재 시간으로 자동 생성됩니다.
- `before`: 비교할 이전 스냅샷 ID. 비우면 저장된 스냅샷 중 직전 데이터를 자동 선택합니다.
- `no_compare`: `true`면 스냅샷만 저장하고 비교는 건너뜁니다.
- `use_existing`: `true`면 원천 랭킹 API 추출을 건너뛰고 기존 JSON만 가공합니다.

API 토큰은 가능하면 GitHub Secrets의 `PRASIA_API_TOKEN`에 저장해서 사용하세요.
스크립트에는 기존 방식과의 호환을 위한 기본값도 남겨두었습니다.

## 비교 기준

- 일반 결사원 닉네임은 기본 점수 산정에서 제외합니다.
- 결사장 닉네임은 주요 기준으로 사용합니다.
- 결사명은 변경/선점 가능성이 있으므로 보너스 기준으로만 사용합니다.
- 91레벨 이상 멤버의 레벨 분포, 직업군 분포, 레벨별 직업군 분포를 핵심 기준으로 사용합니다.
- 결사순위 점수는 후보 정렬 및 근접도 보정값으로 사용합니다.
