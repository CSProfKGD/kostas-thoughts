const state = {
  posts: [],
  activeTopic: "All",
  query: "",
  sort: "newest",
};

const collapsedLineCount = 6;
let resizeTimer;

const topicOrder = [
  "Teaching & Presentations",
  "Peer Review & Conferences",
  "Research Practice",
  "Academia & Faculty Life",
  "Mentoring & Students",
  "AI & Tools",
  "Career",
  "Productivity",
  "Personal Reflections",
  "Humour",
  "Miscellaneous",
];

const els = {
  postCount: document.querySelector("#post-count"),
  search: document.querySelector("#search-input"),
  sort: document.querySelector("#sort-select"),
  filters: document.querySelector("#topic-filters"),
  summary: document.querySelector("#results-summary"),
  posts: document.querySelector("#posts-container"),
  themeToggle: document.querySelector("#theme-toggle"),
};

function normalize(value) {
  return String(value || "").toLowerCase();
}

function dateValue(post) {
  return post.date ? Date.parse(`${post.date}T00:00:00Z`) : 0;
}

function postMatches(post) {
  const query = normalize(state.query).trim();
  const topicMatch = state.activeTopic === "All" || post.topic === state.activeTopic;
  if (!topicMatch) return false;
  if (!query) return true;

  const haystack = [
    post.title,
    post.date,
    post.text,
    post.url,
    post.topic,
    post.subtopic,
  ].map(normalize).join(" ");

  return haystack.includes(query);
}

function sortPosts(posts) {
  const direction = state.sort === "oldest" ? 1 : -1;
  return [...posts].sort((a, b) => {
    const dateDiff = (dateValue(a) - dateValue(b)) * direction;
    if (dateDiff !== 0) return dateDiff;
    return String(a.id).localeCompare(String(b.id)) * direction;
  });
}

function groupedByTopic(posts) {
  const groups = new Map();
  for (const post of posts) {
    const topic = post.topic || "Miscellaneous";
    if (!groups.has(topic)) groups.set(topic, []);
    groups.get(topic).push(post);
  }

  return [...groups.entries()].sort(([a], [b]) => {
    const ai = topicOrder.indexOf(a);
    const bi = topicOrder.indexOf(b);
    if (ai === -1 && bi === -1) return a.localeCompare(b);
    if (ai === -1) return 1;
    if (bi === -1) return -1;
    return ai - bi;
  });
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function cleanThoughtText(text) {
  return String(text || "").replace(/^\s*#kostasthoughts\s*:?\s*/i, "").trim();
}

function bodyText(post) {
  const text = String(post.text || "")
    .replace(/\bSource:\s*/gi, "")
    .replace(/https?:\/\/\S+/g, "")
    .replace(/pic\.twitter\.com\/\S+/g, "")
    .replace(/\s+/g, " ")
    .trim();
  return cleanThoughtText(text);
}

function applyTheme(theme) {
  const nextTheme = theme === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = nextTheme;
  localStorage.setItem("theme", nextTheme);
  if (els.themeToggle) {
    els.themeToggle.textContent = nextTheme === "dark" ? "☀ Light" : "☾ Dark";
    els.themeToggle.setAttribute("aria-pressed", String(nextTheme === "dark"));
  }
}

function renderFilters() {
  const topics = ["All", ...new Set(state.posts.map((post) => post.topic || "Miscellaneous"))];
  els.filters.innerHTML = topics.map((topic) => {
    const count = topic === "All"
      ? state.posts.length
      : state.posts.filter((post) => (post.topic || "Miscellaneous") === topic).length;
    const active = topic === state.activeTopic ? " active" : "";
    return `<button class="topic-button${active}" type="button" data-topic="${escapeHtml(topic)}">${escapeHtml(topic)} (${count})</button>`;
  }).join("");
}

function renderPosts() {
  const filtered = sortPosts(state.posts.filter(postMatches));
  els.postCount.textContent = `${state.posts.length} posts`;
  els.summary.textContent = `${filtered.length} ${filtered.length === 1 ? "post" : "posts"} shown`;

  if (filtered.length === 0) {
    els.posts.innerHTML = `<div class="empty">No posts match the current filters.</div>`;
    return;
  }

  els.posts.innerHTML = groupedByTopic(filtered).map(([topic, posts]) => `
    <section class="topic-group">
      <div class="topic-heading">
        <h2>${escapeHtml(topic)}</h2>
        <span>${posts.length} ${posts.length === 1 ? "post" : "posts"}</span>
      </div>
      <div class="post-list">
        ${posts.map((post) => renderPost(post)).join("")}
      </div>
    </section>
  `).join("");

  requestAnimationFrame(setupCollapsiblePosts);
}

function renderPost(post) {
  const date = post.date || "Date unavailable";
  const subtopic = post.subtopic ? ` · ${escapeHtml(post.subtopic)}` : "";
  const question = post.summary_question || post.title;
  const text = bodyText(post);
  const link = post.url
    ? `<a class="question-link" href="${escapeHtml(post.url)}" rel="noreferrer">${escapeHtml(question)}</a>`
    : `<span class="question-link">${escapeHtml(question)}</span>`;

  return `
    <article class="post-card">
      <div class="post-header">
        <h3 class="post-title">${link}</h3>
        <time class="post-date" datetime="${escapeHtml(post.date || "")}">${escapeHtml(date)}</time>
      </div>
      ${text ? `
        <div class="post-body">
          <p class="post-text">${escapeHtml(text)}</p>
        </div>
        <button class="read-toggle" type="button" aria-expanded="false" hidden>Read more →</button>
      ` : ""}
      <div class="post-meta">
        <span class="topic-tag">${escapeHtml(post.topic || "Miscellaneous")}${subtopic}</span>
      </div>
    </article>
  `;
}

function setupCollapsiblePosts() {
  document.querySelectorAll(".post-card").forEach((card) => {
    const body = card.querySelector(".post-body");
    const text = card.querySelector(".post-text");
    const button = card.querySelector(".read-toggle");
    if (!body || !text || !button) return;

    card.classList.remove("is-collapsible", "is-expanded");
    button.hidden = true;
    button.textContent = "Read more →";
    button.setAttribute("aria-expanded", "false");

    if (renderedLineCount(text) > collapsedLineCount) {
      card.classList.add("is-collapsible");
      button.hidden = false;
    }
  });
}

function renderedLineCount(element) {
  const range = document.createRange();
  range.selectNodeContents(element);
  const tops = [...range.getClientRects()].map((rect) => Math.round(rect.top));
  range.detach();

  if (tops.length > 0) {
    return new Set(tops).size;
  }

  const style = window.getComputedStyle(element);
  const lineHeight = Number.parseFloat(style.lineHeight);
  const fontSize = Number.parseFloat(style.fontSize);
  const resolvedLineHeight = Number.isFinite(lineHeight) ? lineHeight : fontSize * 1.55;
  return Math.ceil(element.scrollHeight / resolvedLineHeight);
}

function queueCollapsibleRefresh() {
  window.clearTimeout(resizeTimer);
  resizeTimer = window.setTimeout(setupCollapsiblePosts, 120);
}

function update() {
  renderFilters();
  renderPosts();
}

async function loadPosts() {
  try {
    const response = await fetch("posts.json", { cache: "no-store" });
    if (!response.ok) throw new Error(`Unable to load posts.json (${response.status})`);
    const data = await response.json();
    state.posts = Array.isArray(data.posts) ? data.posts : [];
    update();
  } catch (error) {
    els.postCount.textContent = "Offline";
    els.summary.textContent = "Could not load posts.json.";
    els.posts.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
  }
}

els.search.addEventListener("input", (event) => {
  state.query = event.target.value;
  renderPosts();
});

els.sort.addEventListener("change", (event) => {
  state.sort = event.target.value;
  renderPosts();
});

els.filters.addEventListener("click", (event) => {
  const button = event.target.closest("[data-topic]");
  if (!button) return;
  state.activeTopic = button.dataset.topic;
  update();
});

els.posts.addEventListener("click", (event) => {
  const button = event.target.closest(".read-toggle");
  if (!button) return;

  const card = button.closest(".post-card");
  if (!card) return;

  const expanded = card.classList.toggle("is-expanded");
  button.textContent = expanded ? "Show less ↑" : "Read more →";
  button.setAttribute("aria-expanded", String(expanded));
});

els.themeToggle?.addEventListener("click", () => {
  const current = document.documentElement.dataset.theme;
  applyTheme(current === "dark" ? "light" : "dark");
});

window.addEventListener("resize", queueCollapsibleRefresh);

applyTheme(document.documentElement.dataset.theme);
loadPosts();
