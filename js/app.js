const DEFAULT_COMPARE_URL = "./data/compare/latest.json";
const GUILD_SCORE_URL = "./data/Who_are_you_guild_score.json";

const state = {
  data: null,
  matches: [],
  snapshotsInitialized: false,
  guildRankMap: new Map()
};

const gradeConfig = [
  { min: 85, key: "very-high", label: "매우 유력", className: "grade-very-high" },
  { min: 70, key: "high", label: "유력", className: "grade-high" },
  { min: 55, key: "possible", label: "가능성 있음", className: "grade-possible" },
  { min: 0, key: "low", label: "낮음", className: "grade-low" }
];

const weightLabels = {
  master: "결사장 일치/유사도",
  level_class_distribution: "91+ 레벨별 직업군 분포",
  level_distribution: "91+ 레벨 분포",
  class_distribution: "91+ 전체 직업군 분포",
  high_level_count: "91+ 총 인원 유사도",
  guild_score_closeness: "결사순위 점수 근접도",
  guild_name_bonus: "결사명 보너스"
};

const sidebar = document.getElementById("sidebar");
const dim = document.getElementById("mobileDim");
const modal = document.getElementById("detailModal");
const modalBody = document.getElementById("detailModalBody");
const modalTitle = document.getElementById("detailModalTitle");

function formatNumber(value, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return Number(value).toLocaleString("ko-KR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  });
}


function mapServerName(value) {
  const raw = String(value ?? "").trim();
  if (!raw || raw === "-") return "-";
  const mappings = window.PRASIA_MAPPINGS?.servers || {};
  if (mappings[raw]) return mappings[raw];

  const compact = raw.replace(/^LIVE_W/i, "").replace(/^W/i, "");
  const channel = String(value ?? "").match(/(?:-|_)(\d+)$/)?.[1];
  const worldNumber = compact.match(/\d+/)?.[0];
  if (worldNumber && channel) {
    const normalized = `${Number(worldNumber)}-${Number(channel)}`;
    if (mappings[normalized]) return mappings[normalized];
  }

  return raw;
}

function mapClassName(value) {
  const raw = String(value ?? "").trim();
  if (!raw || raw === "-") return "-";
  return window.PRASIA_MAPPINGS?.classes?.[raw] || raw;
}

function decorateGuild(guild = {}) {
  return {
    ...guild,
    server_label: mapServerName(guild.server ?? guild.world ?? guild.world_id),
  };
}

function getGrade(score) {
  return gradeConfig.find((item) => score >= item.min) || gradeConfig[gradeConfig.length - 1];
}

function getFilterMin(filterValue) {
  if (filterValue === "very-high") return 85;
  if (filterValue === "high") return 70;
  if (filterValue === "possible") return 55;
  return 0;
}

function normalizeKeyword(value) {
  return String(value || "").trim().toLowerCase();
}

function rankKey(guild = {}) {
  return [guild.server, guild.guild_name, guild.guild_master].map((value) => normalizeKeyword(value)).join("|");
}

function fallbackRankKey(guild = {}) {
  return [guild.guild_name, guild.guild_master].map((value) => normalizeKeyword(value)).join("|");
}

async function loadGuildScoreOrder() {
  try {
    const response = await fetch(`${GUILD_SCORE_URL}?v=${Date.now()}`);
    if (!response.ok) return;
    const data = await response.json();
    const rankings = Array.isArray(data.rankings) ? data.rankings : [];
    rankings.forEach((item, index) => {
      const rankValue = Number(item.rank || item.previous_rank || index + 1);
      const mapped = {
        rank: rankValue,
        score: Number(item.score || item.previous_score || 0)
      };
      state.guildRankMap.set(rankKey({ server: item.world, guild_name: item.guild_name, guild_master: item.guild_master }), mapped);
      state.guildRankMap.set(fallbackRankKey({ guild_name: item.guild_name, guild_master: item.guild_master }), mapped);
    });
  } catch (error) {
    console.warn("상위권 정렬 기준 데이터를 불러오지 못했습니다.", error);
  }
}

function getBaseOrder(match) {
  const before = match.before || {};
  const found = state.guildRankMap.get(rankKey(before)) || state.guildRankMap.get(fallbackRankKey(before));
  if (found) return found.rank;
  return Number(before.guild_rank || 999999);
}

function sortMatches(matches) {
  return [...matches].sort((a, b) => {
    const rankDiff = getBaseOrder(a) - getBaseOrder(b);
    if (rankDiff !== 0) return rankDiff;
    return Number(b.similarity || 0) - Number(a.similarity || 0);
  });
}

function moveToSection(sectionId) {
  document.querySelectorAll(".page").forEach((page) => page.classList.remove("active"));
  document.querySelectorAll(".side-menu-item[data-section]").forEach((button) => button.classList.remove("active"));

  const page = document.getElementById(sectionId);
  const button = document.querySelector(`[data-section="${sectionId}"]`);

  if (page) page.classList.add("active");
  if (button) button.classList.add("active");

  closeMenu();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function closeMenu() {
  if (sidebar) sidebar.classList.remove("open");
  if (dim) dim.classList.remove("open");
}

function getSnapshotLabel(snapshot) {
  if (!snapshot) return "-";
  const list = state.data?.meta?.available_snapshots || [];
  const found = list.find((item) => item.id === snapshot);
  return found?.label || snapshot;
}

function renderSnapshotSelectors(data) {
  const beforeSelect = document.getElementById("beforeSnapshotSelect");
  const afterSelect = document.getElementById("afterSnapshotSelect");
  if (!beforeSelect || !afterSelect) return;

  const meta = data.meta || {};
  const snapshots = Array.isArray(meta.available_snapshots) && meta.available_snapshots.length
    ? meta.available_snapshots
    : [
        { id: meta.before_snapshot, label: meta.before_snapshot },
        { id: meta.after_snapshot, label: meta.after_snapshot }
      ].filter((item) => item.id);

  const options = snapshots.map((item) => `<option value="${item.id}">${item.label || item.id}</option>`).join("");
  beforeSelect.innerHTML = options;
  afterSelect.innerHTML = options;
  beforeSelect.value = meta.before_snapshot || snapshots[0]?.id || "";
  afterSelect.value = meta.after_snapshot || snapshots[snapshots.length - 1]?.id || "";
  state.snapshotsInitialized = true;
}

function renderSummary(data) {
  const summaryGrid = document.getElementById("summaryGrid");
  const matches = data.matches || [];
  const veryHighCount = matches.filter((item) => item.similarity >= 85).length;
  const maxScore = matches.length ? Math.max(...matches.map((item) => Number(item.similarity || 0))) : 0;

  summaryGrid.innerHTML = `
    <article class="summary-card accent">
      <small>이전 데이터</small>
      <strong>${getSnapshotLabel(data.meta?.before_snapshot)}</strong>
      <span>비교 기준이 되는 이동 전 데이터</span>
    </article>
    <article class="summary-card accent">
      <small>이후 데이터</small>
      <strong>${getSnapshotLabel(data.meta?.after_snapshot)}</strong>
      <span>이동 이후 후보 데이터</span>
    </article>
    <article class="summary-card">
      <small>유사 후보</small>
      <strong>${formatNumber(matches.length)}건</strong>
      <span>상위 결사 기준으로 정렬된 후보</span>
    </article>
    <article class="summary-card">
      <small>최고 유사도</small>
      <strong>${formatNumber(maxScore, 1)}점</strong>
      <span>매우 유력 후보 ${formatNumber(veryHighCount)}건</span>
    </article>
  `;
}

function renderWeights(weights = {}) {
  const weightList = document.getElementById("weightList");
  if (!weightList) return;

  weightList.innerHTML = Object.entries(weights).map(([key, value]) => `
    <div class="weight-row">
      <strong>${weightLabels[key] || key}</strong>
      <span>${value}점</span>
    </div>
  `).join("");
}

function guildCell(guild) {
  const view = decorateGuild(guild || {});
  return `
    <span class="guild-name">${view.guild_name || "-"}</span>
    <span class="guild-meta">${view.server_label || "-"} · 결사장 ${view.guild_master || "-"}</span>
  `;
}

function renderMatches() {
  const tbody = document.getElementById("matchTableBody");
  const gradeFilter = document.getElementById("gradeFilter").value;
  const keyword = normalizeKeyword(document.getElementById("keywordFilter").value);
  const minScore = getFilterMin(gradeFilter);

  const filtered = state.matches.filter((item) => {
    const score = Number(item.similarity || 0);
    const text = normalizeKeyword([
      item.before?.server,
      mapServerName(item.before?.server),
      item.before?.guild_name,
      item.before?.guild_master,
      item.after?.server,
      mapServerName(item.after?.server),
      item.after?.guild_name,
      item.after?.guild_master
    ].join(" "));

    return score >= minScore && (!keyword || text.includes(keyword));
  });

  if (!filtered.length) {
    tbody.innerHTML = `<tr><td colspan="8" class="empty-cell">조건에 맞는 후보가 없습니다.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map((item) => {
    const grade = getGrade(Number(item.similarity || 0));
    const evidence = (item.evidence || []).slice(0, 3).map((tag) => `<span class="evidence-tag">${tag}</span>`).join("");

    return `
      <tr>
        <td>${guildCell(item.before || {})}</td>
        <td>${formatNumber(item.before?.guild_rank)}위</td>
        <td>${guildCell(item.after || {})}</td>
        <td>${formatNumber(item.after?.guild_rank)}위</td>
        <td><span class="score-pill">${formatNumber(item.similarity, 1)}</span></td>
        <td><span class="grade-pill ${grade.className}">${item.grade || grade.label}</span></td>
        <td><div class="evidence-list">${evidence}</div></td>
        <td><button class="detail-button" type="button" data-match-id="${item.id}">보기</button></td>
      </tr>
    `;
  }).join("");
}

function distributionTable(title, before = {}, after = {}) {
  const keys = Array.from(new Set([...Object.keys(before || {}), ...Object.keys(after || {})])).sort((a, b) => Number(b) - Number(a) || a.localeCompare(b, "ko"));

  const rows = keys.map((key) => `
    <tr>
      <td>${key}</td>
      <td>${formatNumber(before?.[key])}</td>
      <td>${formatNumber(after?.[key])}</td>
    </tr>
  `).join("") || `<tr><td colspan="3">데이터 없음</td></tr>`;

  return `
    <div class="detail-section">
      <h3>${title}</h3>
      <table class="dist-table">
        <thead><tr><th>구분</th><th>이전</th><th>이후</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>
  `;
}

function levelClassSummary(value = {}) {
  const levels = Object.keys(value || {}).sort((a, b) => Number(b) - Number(a));
  if (!levels.length) return "데이터 없음";

  return levels.map((level) => {
    const classes = Object.entries(value[level] || {})
      .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "ko"))
      .map(([className, count]) => `${className} ${count}`)
      .join(" · ");
    return `<strong>${level}레벨</strong><span>${classes || "-"}</span>`;
  }).join("<br>");
}

function scoreBreakdown(scores = {}, weights = {}) {
  return Object.entries(weights).map(([key, max]) => {
    const value = Number(scores[key] || 0);
    const percent = max ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
    return `
      <div class="score-row">
        <span>${weightLabels[key] || key}</span>
        <div class="score-bar"><span style="width:${percent}%"></span></div>
        <b>${formatNumber(value, 1)}</b>
      </div>
    `;
  }).join("");
}

function memberKey(member = {}) {
  return [
    normalizeKeyword(member.nickname || member.name),
    String(member.level || ""),
    normalizeKeyword(mapClassName(member.class || member.class_name)),
  ].join("|");
}

function normalizeMembers(members = [], masterName = "") {
  const seen = new Set();
  const normalized = [];
  const masterKey = normalizeKeyword(masterName);

  (Array.isArray(members) ? members : []).forEach((member) => {
    const nickname = String(member.nickname || member.name || "-").trim();
    const row = {
      ...member,
      nickname,
      class: mapClassName(member.class || member.class_name),
      is_master: Boolean(member.is_master) || (!!masterKey && normalizeKeyword(nickname) === masterKey),
    };
    const key = memberKey(row);
    if (seen.has(key)) return;
    seen.add(key);
    normalized.push(row);
  });

  return normalized.sort((a, b) => {
    if (a.is_master !== b.is_master) return a.is_master ? -1 : 1;
    return Number(b.level || 0) - Number(a.level || 0) || String(a.nickname).localeCompare(String(b.nickname), "ko");
  });
}

function memberRows(members = [], masterName = "") {
  const rows = normalizeMembers(members, masterName);
  if (!rows.length) {
    return `<tr><td colspan="3" class="member-empty">표시할 멤버 데이터가 없습니다.</td></tr>`;
  }
  return rows.map((member) => `
    <tr class="${member.is_master ? "member-master" : ""}">
      <td>${member.nickname || member.name || "-"}</td>
      <td>${formatNumber(member.level)}</td>
      <td>${member.class || member.class_name || "-"}</td>
    </tr>
  `).join("");
}

function memberTable(title, members = [], masterName = "") {
  return `
    <section class="detail-section">
      <h3>${title}</h3>
      <table class="member-table">
        <thead><tr><th>닉네임</th><th>레벨</th><th>직업군</th></tr></thead>
        <tbody>${memberRows(members, masterName)}</tbody>
      </table>
    </section>
  `;
}

function openDetail(matchId) {
  const match = state.matches.find((item) => item.id === matchId);
  if (!match) return;

  const beforeView = decorateGuild(match.before || {});
  const afterView = decorateGuild(match.after || {});

  modalTitle.textContent = `${beforeView.guild_name || "-"} → ${afterView.guild_name || "-"}`;
  modalBody.innerHTML = `
    <div class="detail-grid">
      <div class="detail-box">
        <small>이전 결사</small>
        <strong>${beforeView.server_label || "-"} / ${beforeView.guild_name || "-"}</strong>
        <span class="guild-meta">결사장 ${beforeView.guild_master || "-"} · ${formatNumber(match.before?.guild_rank)}위 · 점수 ${formatNumber(match.before?.guild_score, 2)}</span>
      </div>
      <div class="detail-box">
        <small>이후 후보</small>
        <strong>${afterView.server_label || "-"} / ${afterView.guild_name || "-"}</strong>
        <span class="guild-meta">결사장 ${afterView.guild_master || "-"} · ${formatNumber(match.after?.guild_rank)}위 · 점수 ${formatNumber(match.after?.guild_score, 2)}</span>
      </div>
      <div class="detail-box">
        <small>유사도</small>
        <strong>${formatNumber(match.similarity, 1)}점</strong>
        <span class="guild-meta">판정 ${match.grade || getGrade(match.similarity).label}</span>
      </div>
      <div class="detail-box">
        <small>91+ 표본</small>
        <strong>${formatNumber(match.before?.high_level_count)}명 → ${formatNumber(match.after?.high_level_count)}명</strong>
        <span class="guild-meta">결사장 포함 고레벨 구성 참고</span>
      </div>
    </div>

    <section class="detail-section">
      <h3>항목별 점수</h3>
      <div class="score-breakdown">${scoreBreakdown(match.scores || {}, state.data?.weights || {})}</div>
    </section>

    <div class="distribution-grid">
      ${distributionTable("91+ 레벨 분포", match.before?.level_distribution, match.after?.level_distribution)}
      ${distributionTable("91+ 직업군 분포", match.before?.class_distribution, match.after?.class_distribution)}
    </div>

    <section class="detail-section">
      <h3>레벨별 직업군 분포</h3>
      <div class="distribution-grid">
        <div class="detail-box"><small>이전</small>${levelClassSummary(match.before?.level_class_distribution)}</div>
        <div class="detail-box"><small>이후</small>${levelClassSummary(match.after?.level_class_distribution)}</div>
      </div>
    </section>

    <div class="member-compare-grid">
      ${memberTable("이전 멤버", match.before?.members || [], beforeView.guild_master)}
      ${memberTable("이후 멤버", match.after?.members || [], afterView.guild_master)}
    </div>
  `;

  modal.classList.add("open");
  modal.setAttribute("aria-hidden", "false");
  document.body.style.overflow = "hidden";
}

function closeDetail() {
  modal.classList.remove("open");
  modal.setAttribute("aria-hidden", "true");
  document.body.style.overflow = "";
}

function getCompareUrl(before, after) {
  if (!before || !after) return DEFAULT_COMPARE_URL;
  return `./data/compare/${before}__${after}.json`;
}

async function loadData(url = DEFAULT_COMPARE_URL, keepSelectors = false) {
  const dataStatus = document.getElementById("dataStatus");

  try {
    const response = await fetch(`${url}?v=${Date.now()}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();
    state.data = data;
    state.matches = sortMatches(Array.isArray(data.matches) ? data.matches : []);

    dataStatus.textContent = `비교 생성 ${data.meta?.created_at || "-"}`;
    dataStatus.classList.remove("error");

    if (!state.snapshotsInitialized || !keepSelectors) renderSnapshotSelectors(data);
    renderSummary(data);
    renderWeights(data.weights || {});
    renderMatches();
  } catch (error) {
    console.error(error);
    dataStatus.textContent = "데이터 로드 실패";
    dataStatus.classList.add("error");
    document.getElementById("matchTableBody").innerHTML = `<tr><td colspan="8" class="empty-cell">선택한 비교 데이터를 불러오지 못했습니다.</td></tr>`;
  }
}

async function applySnapshotSelection() {
  const before = document.getElementById("beforeSnapshotSelect")?.value;
  const after = document.getElementById("afterSnapshotSelect")?.value;
  await loadData(getCompareUrl(before, after), true);
}

document.querySelectorAll(".side-menu-item[data-section]").forEach((button) => {
  button.addEventListener("click", () => moveToSection(button.dataset.section));
});

document.getElementById("mobileMenuButton")?.addEventListener("click", () => {
  sidebar.classList.add("open");
  dim.classList.add("open");
});

dim?.addEventListener("click", closeMenu);

document.getElementById("gradeFilter")?.addEventListener("change", renderMatches);
document.getElementById("keywordFilter")?.addEventListener("input", renderMatches);
document.getElementById("applySnapshotButton")?.addEventListener("click", applySnapshotSelection);

document.getElementById("matchTableBody")?.addEventListener("click", (event) => {
  const button = event.target.closest("[data-match-id]");
  if (button) openDetail(button.dataset.matchId);
});

document.getElementById("detailModalClose")?.addEventListener("click", closeDetail);
modal?.addEventListener("click", (event) => {
  if (event.target === modal) closeDetail();
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeDetail();
    closeMenu();
  }
});

(async function init() {
  await loadGuildScoreOrder();
  await loadData();
})();
