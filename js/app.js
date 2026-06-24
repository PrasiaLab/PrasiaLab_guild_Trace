const DATA_URL = "./data/compare/latest.json";

const state = {
  data: null,
  matches: []
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

function renderSummary(data) {
  const summaryGrid = document.getElementById("summaryGrid");
  const matches = data.matches || [];
  const veryHighCount = matches.filter((item) => item.similarity >= 85).length;
  const maxScore = matches.length ? Math.max(...matches.map((item) => Number(item.similarity || 0))) : 0;

  summaryGrid.innerHTML = `
    <article class="summary-card accent">
      <small>이전 스냅샷</small>
      <strong>${data.meta?.before_snapshot || "-"}</strong>
      <span>비교 기준이 되는 서버 이동 전 데이터</span>
    </article>
    <article class="summary-card accent">
      <small>이후 스냅샷</small>
      <strong>${data.meta?.after_snapshot || "-"}</strong>
      <span>서버 이동 이후 후보 데이터</span>
    </article>
    <article class="summary-card">
      <small>유사 후보</small>
      <strong>${formatNumber(matches.length)}건</strong>
      <span>latest.json 기준으로 계산된 후보</span>
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
  return `
    <span class="guild-name">${guild.guild_name || "-"}</span>
    <span class="guild-meta">${guild.server || "-"} · 결사장 ${guild.guild_master || "-"}</span>
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
      item.before?.guild_name,
      item.before?.guild_master,
      item.after?.server,
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

function openDetail(matchId) {
  const match = state.matches.find((item) => item.id === matchId);
  if (!match) return;

  modalTitle.textContent = `${match.before?.guild_name || "-"} → ${match.after?.guild_name || "-"}`;
  modalBody.innerHTML = `
    <div class="detail-grid">
      <div class="detail-box">
        <small>이전 결사</small>
        <strong>${match.before?.server || "-"} / ${match.before?.guild_name || "-"}</strong>
        <span class="guild-meta">결사장 ${match.before?.guild_master || "-"} · ${formatNumber(match.before?.guild_rank)}위 · 점수 ${formatNumber(match.before?.guild_score, 2)}</span>
      </div>
      <div class="detail-box">
        <small>이후 후보</small>
        <strong>${match.after?.server || "-"} / ${match.after?.guild_name || "-"}</strong>
        <span class="guild-meta">결사장 ${match.after?.guild_master || "-"} · ${formatNumber(match.after?.guild_rank)}위 · 점수 ${formatNumber(match.after?.guild_score, 2)}</span>
      </div>
      <div class="detail-box">
        <small>유사도</small>
        <strong>${formatNumber(match.similarity, 1)}점</strong>
        <span class="guild-meta">판정 ${match.grade || getGrade(match.similarity).label}</span>
      </div>
      <div class="detail-box">
        <small>91+ 표본</small>
        <strong>${formatNumber(match.before?.high_level_count)}명 → ${formatNumber(match.after?.high_level_count)}명</strong>
        <span class="guild-meta">일반 결사원 닉네임은 비교 기준 제외</span>
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

async function loadData() {
  const dataStatus = document.getElementById("dataStatus");

  try {
    const response = await fetch(`${DATA_URL}?v=${Date.now()}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    const data = await response.json();
    state.data = data;
    state.matches = Array.isArray(data.matches) ? data.matches : [];

    dataStatus.textContent = `비교 생성 ${data.meta?.created_at || "-"}`;
    dataStatus.classList.remove("error");

    renderSummary(data);
    renderWeights(data.weights || {});
    renderMatches();
  } catch (error) {
    console.error(error);
    dataStatus.textContent = "데이터 로드 실패";
    dataStatus.classList.add("error");
    document.getElementById("matchTableBody").innerHTML = `<tr><td colspan="8" class="empty-cell">data/compare/latest.json을 불러오지 못했습니다.</td></tr>`;
  }
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

loadData();
