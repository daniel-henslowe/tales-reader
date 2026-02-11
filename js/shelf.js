/* === Magazine Shelf === */
(function () {
  'use strict';

  let manifest = null;
  let activeEra = 'all';
  let activeYear = null;

  const grid = document.getElementById('issue-grid');
  const countEl = document.getElementById('issue-count');
  const yearFilters = document.getElementById('year-filters');

  async function init() {
    const resp = await fetch('data/manifest.json');
    manifest = await resp.json();
    buildYearPills();
    render();
  }

  function buildYearPills() {
    manifest.years.forEach(year => {
      const btn = document.createElement('button');
      btn.className = 'filter-btn';
      btn.dataset.year = year;
      btn.textContent = year;
      btn.addEventListener('click', () => filterByYear(year));
      yearFilters.appendChild(btn);
    });
  }

  function filterByEra(era) {
    activeEra = era;
    activeYear = null;
    updateFilterUI();
    render();
  }

  function filterByYear(year) {
    if (activeYear === year) {
      activeYear = null;
    } else {
      activeYear = year;
      // Auto-set era based on year
      activeEra = year <= 1956 ? 'era-I' : year >= 1964 ? 'era-II' : 'all';
    }
    updateFilterUI();
    render();
  }

  function updateFilterUI() {
    document.querySelectorAll('#era-filters .filter-btn').forEach(btn => {
      btn.classList.toggle('filter-btn--active', btn.dataset.filter === activeEra);
    });
    document.querySelectorAll('#year-filters .filter-btn').forEach(btn => {
      btn.classList.toggle('filter-btn--active', btn.dataset.year == activeYear);
    });
  }

  function getFilteredIssues() {
    return manifest.issues.filter(issue => {
      if (activeYear && issue.year !== activeYear) return false;
      if (activeEra === 'era-I' && issue.era !== 'I') return false;
      if (activeEra === 'era-II' && issue.era !== 'II') return false;
      return true;
    });
  }

  function render() {
    const issues = getFilteredIssues();
    countEl.textContent = `${issues.length} issue${issues.length !== 1 ? 's' : ''}`;

    grid.innerHTML = issues.map(issue => {
      const eraClass = issue.era === 'II' ? ' issue-card--era-ii' : '';
      const stories = issue.stories.slice(0, 3);
      const moreCount = issue.stories.length - 3;

      return `
        <a href="reader.html?issue=${issue.number_padded}" class="issue-card${eraClass}">
          <div class="issue-card__masthead">Tales from the Future<br>and Beyond</div>
          <div class="issue-card__number">#${issue.number} &middot; ${issue.date} &middot; ${issue.cover_price}</div>
          ${issue.cover_art ? `
            <div class="issue-card__cover-art">&ldquo;${escapeHtml(issue.cover_art.title)}&rdquo;</div>
            <div class="issue-card__cover-artist">by ${escapeHtml(issue.cover_art.artist)}</div>
          ` : ''}
          <hr class="issue-card__divider">
          <ul class="issue-card__stories">
            ${stories.map(s => `
              <li>&ldquo;${escapeHtml(s.title)}&rdquo; <span class="author">&mdash; ${escapeHtml(s.author)}</span></li>
            `).join('')}
            ${moreCount > 0 ? `<li style="color:var(--text-muted); font-style:italic">+ ${moreCount} more</li>` : ''}
          </ul>
          <div class="issue-card__footer">
            <span class="issue-card__price">${escapeHtml(issue.cover_price)}</span>
            <span class="issue-card__era">Era ${issue.era}</span>
          </div>
        </a>
      `;
    }).join('');
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // Era filter clicks
  document.querySelectorAll('#era-filters .filter-btn').forEach(btn => {
    btn.addEventListener('click', () => filterByEra(btn.dataset.filter));
  });

  // Settings panel
  const settingsToggle = document.getElementById('settings-toggle');
  const settingsPanel = document.getElementById('settings-panel');
  const settingsClose = document.getElementById('settings-close');
  const overlay = document.getElementById('overlay');

  function openSettings() {
    settingsPanel.classList.add('open');
    overlay.classList.add('visible');
  }

  function closeSettings() {
    settingsPanel.classList.remove('open');
    overlay.classList.remove('visible');
  }

  settingsToggle.addEventListener('click', openSettings);
  settingsClose.addEventListener('click', closeSettings);
  overlay.addEventListener('click', closeSettings);

  // Theme buttons
  document.querySelectorAll('[data-theme-choice]').forEach(btn => {
    btn.addEventListener('click', () => {
      const theme = btn.dataset.themeChoice;
      Preferences.setTheme(theme);
      document.querySelectorAll('[data-theme-choice]').forEach(b =>
        b.classList.toggle('btn--active', b.dataset.themeChoice === theme)
      );
    });
  });

  init();
})();
