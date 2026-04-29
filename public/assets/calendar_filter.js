/**
 * 試合日程カレンダー - フィルタ & アコーディオン & 週折りたたみ制御
 */

/**
 * コンペティションカードのトグル
 */
function toggleCard(cardElement) {
    const isActive = cardElement.classList.toggle('active');
    cardElement.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    applyFilter();
}

/**
 * フィルタを適用する
 */
function applyFilter() {
    const activeLeagues = Array.from(document.querySelectorAll('.competition-card.active')).map(el => el.getAttribute('data-league'));

    document.querySelectorAll('.league-column').forEach(column => {
        const leagueName = column.getAttribute('data-league');
        if (activeLeagues.includes(leagueName)) {
            column.style.display = 'flex';
        } else {
            column.style.display = 'none';
        }
    });

    document.querySelectorAll('.week-section').forEach(section => {
        const visibleColumns = Array.from(section.querySelectorAll('.league-column')).filter(col => col.style.display !== 'none');
        section.style.display = visibleColumns.length === 0 ? 'none' : 'block';
    });
}

/**
 * 全選択/全解除
 */
function selectAll(active) {
    document.querySelectorAll('.competition-card').forEach(card => {
        if (active) {
            card.classList.add('active');
            card.setAttribute('aria-pressed', 'true');
        } else {
            card.classList.remove('active');
            card.setAttribute('aria-pressed', 'false');
        }
    });
    applyFilter();
}

/**
 * 試合行のアコーディオンを切り替える
 */
function toggleAccordion(rowElement) {
    rowElement.classList.toggle('active');
}

/**
 * 週セクションの折りたたみを切り替える
 */
function toggleWeekSection(headerElement) {
    const section = headerElement.closest('.week-section');
    section.classList.toggle('collapsed');
}

// ページロード時にフィルタを初期適用
document.addEventListener('DOMContentLoaded', () => {
    applyFilter();
});
