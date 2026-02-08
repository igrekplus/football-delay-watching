/**
 * 試合日程カレンダー - フィルタ & アコーディオン & 週折りたたみ制御
 */

/**
 * フィルタを適用する
 */
function applyFilter() {
    const checkedLeagues = Array.from(document.querySelectorAll('.league-filter:checked')).map(el => el.value);

    document.querySelectorAll('.league-column').forEach(column => {
        const leagueName = column.getAttribute('data-league');
        if (checkedLeagues.includes(leagueName)) {
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
function selectAll(checked) {
    document.querySelectorAll('.league-filter').forEach(el => el.checked = checked);
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
