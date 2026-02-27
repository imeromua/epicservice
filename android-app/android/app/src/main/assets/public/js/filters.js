/**
 * filters.js - Product filters sidebar for EpicService Android
 */
const EpicFilters = (function() {
    'use strict';

    function _esc(str) {
        return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    var selectedDepts = [];
    var selectedSort = 'balance_sum';
    var _allDepts = [];

    async function init() {
        try {
            var token = App.getToken();
            var data = await EpicAPI.get('/api/products/departments', token);
            _allDepts = data.departments || [];
            _renderDeptList();
        } catch (e) {
            var el = document.getElementById('filters-dept-list');
            if (el) el.innerHTML = '<div style="font-size:14px;font-weight:600;color:var(--text-secondary);margin-bottom:8px">🏢 Відділи</div>' +
                '<div style="font-size:13px;color:var(--text-muted)">' + e.message + '</div>';
        }
    }

    function _renderDeptList() {
        var el = document.getElementById('filters-dept-list');
        if (!el) return;
        el.innerHTML = '<div style="font-size:14px;font-weight:600;color:var(--text-secondary);margin-bottom:8px">🏢 Відділи</div>' +
            _allDepts.map(function(d, i) {
                var active = selectedDepts.indexOf(d.department) >= 0 ? ' action-btn-primary' : '';
                var deptEsc = _esc(d.department);
                return '<button class="action-btn' + active + '" style="width:100%;margin-bottom:4px;text-align:left;justify-content:space-between;display:flex"' +
                    ' onclick="EpicFilters.toggleDept(' + i + ')">' +
                    '<span>Відділ ' + deptEsc + '</span>' +
                    '<span style="font-size:11px;color:var(--text-muted)">' + (d.count || 0) + '</span>' +
                    '</button>';
            }).join('');
    }

    function openSidebar() {
        var sidebar = document.getElementById('filters-sidebar');
        var overlay = document.getElementById('filters-overlay');
        if (sidebar) sidebar.style.display = 'block';
        if (overlay) overlay.style.display = 'block';
        if (!_allDepts.length) init();
    }

    function closeSidebar() {
        var sidebar = document.getElementById('filters-sidebar');
        var overlay = document.getElementById('filters-overlay');
        if (sidebar) sidebar.style.display = 'none';
        if (overlay) overlay.style.display = 'none';
    }

    function toggleDept(indexOrDept) {
        var dept;
        if (typeof indexOrDept === 'number') {
            dept = _allDepts[indexOrDept] ? _allDepts[indexOrDept].department : null;
        } else {
            dept = indexOrDept;
        }
        if (!dept) return;
        var idx = selectedDepts.indexOf(dept);
        if (idx >= 0) selectedDepts.splice(idx, 1);
        else selectedDepts.push(dept);
        _renderDeptList();
        _updateFilterBadge();
    }

    function setSortBy(sort, btn) {
        selectedSort = sort;
        document.querySelectorAll('#filters-sort-btns .action-btn').forEach(function(b) {
            b.classList.remove('action-btn-primary');
        });
        if (btn) btn.classList.add('action-btn-primary');
    }

    async function apply() {
        try {
            var user = App.getUser();
            var token = App.getToken();
            var data = await EpicAPI.post('/api/products/filter', {
                user_id: user.id,
                departments: selectedDepts,
                sort_by: selectedSort,
                offset: 0,
                limit: 500
            }, token);
            App.renderFilterResults(data.products || [], data.stats);
            closeSidebar();
            App.switchTab('search');
        } catch (e) {
            App.toast(e.message || 'Помилка фільтрування', 'error');
        }
    }

    function reset() {
        selectedDepts = [];
        selectedSort = 'balance_sum';
        _renderDeptList();
        _updateFilterBadge();
        document.querySelectorAll('#filters-sort-btns .action-btn').forEach(function(b) {
            b.classList.remove('action-btn-primary');
        });
        var first = document.querySelector('#filters-sort-btns .action-btn[data-sort="balance_sum"]');
        if (first) first.classList.add('action-btn-primary');
    }

    function updateButtonVisibility() {
        var btn = document.getElementById('filters-float-btn');
        if (!btn) return;
        var isSearch = document.getElementById('content-search') && document.getElementById('content-search').classList.contains('active');
        btn.style.display = isSearch ? 'flex' : 'none';
    }

    function _updateFilterBadge() {
        var btn = document.getElementById('filters-float-btn');
        if (!btn) return;
        var count = selectedDepts.length + (selectedSort !== 'balance_sum' ? 1 : 0);
        var old = btn.querySelector('.filter-badge');
        if (old) old.remove();
        if (count > 0) {
            var badge = document.createElement('span');
            badge.className = 'filter-badge';
            badge.style.cssText = 'position:absolute;top:-4px;right:-4px;background:var(--danger);color:white;border-radius:50%;width:18px;height:18px;font-size:11px;display:flex;align-items:center;justify-content:center';
            badge.textContent = count;
            btn.style.position = 'relative';
            btn.appendChild(badge);
        }
    }

    return { init, openSidebar, closeSidebar, toggleDept, setSortBy, apply, reset, updateButtonVisibility };
})();
