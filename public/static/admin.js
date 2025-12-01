// Professional Admin Panel: list, search/filter, pagination, CRUD via modal
document.addEventListener('DOMContentLoaded', () => {
    const tbody = document.getElementById('users-tbody');
    const searchInput = document.getElementById('search-input');
    const roleFilter = document.getElementById('role-filter');
    const addBtn = document.getElementById('add-user-btn');
    const emptyView = document.getElementById('table-empty');
    const emptyAddBtn = document.getElementById('empty-add');
    const loadingView = document.getElementById('table-loading');
    const modal = document.getElementById('user-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalName = document.getElementById('modal-name');
    const modalEmail = document.getElementById('modal-email');
    const modalPassword = document.getElementById('modal-password');
    const modalRole = document.getElementById('modal-role');
    const modalSave = document.getElementById('modal-save');
    const toast = document.getElementById('toast');

    let users = [];
    let filtered = [];
    let page = 1;
    const pageSize = 8;
    let editingUserId = null;
    let sortKey = 'name';
    let sortDir = 'asc';

    function showToast(msg) {
        if (!toast) return;
        toast.textContent = msg;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 2000);
    }
    function openModal(title) {
        modalTitle.textContent = title;
        modal.classList.add('active');
        // focus management
        setTimeout(() => modalName?.focus(), 50);
    }
    function closeModal() {
        modal.classList.remove('active');
        editingUserId = null;
        modalName.value = '';
        modalEmail.value = '';
        modalPassword.value = '';
        modalRole.value = 'user';
    }
    function roleBadge(role) {
        const cls = role === 'admin' ? 'role-badge role-admin' : 'role-badge role-user';
        const label = role === 'admin' ? 'Admin' : 'User';
        return `<span class="${cls}">${label}</span>`;
    }
    function paginate(list) {
        const start = (page - 1) * pageSize;
        return list.slice(start, start + pageSize);
    }
    function renderPageInfo() {
        const info = document.getElementById('page-info');
        const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
        info.textContent = `${page} / ${totalPages}`;
    }
    function renderStats() {
        const total = users.length;
        const admins = users.filter(u => u.role === 'admin').length;
        const standard = total - admins;
        document.getElementById('statUsers').textContent = String(total);
        document.getElementById('statAdmins').textContent = String(admins);
        document.getElementById('statStandard').textContent = String(standard);
    }
    function renderTable() {
        tbody.innerHTML = '';
        const isEmpty = filtered.length === 0;
        if (emptyView) emptyView.hidden = !isEmpty;
        if (loadingView) loadingView.hidden = true;
        const rows = paginate(filtered);
        for (const u of rows) {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${u.id}</td>
                <td>${u.name}</td>
                <td>${u.email}</td>
                <td>${roleBadge(u.role)}</td>
                <td>
                    <div class="table-actions">
                        <button class="btn-secondary" data-edit-id="${u.id}"><i class="fas fa-edit"></i></button>
                        <button class="btn-danger" data-delete-id="${u.id}"><i class="fas fa-trash"></i></button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        }
        renderPageInfo();
        tbody.querySelectorAll('[data-edit-id]').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = Number(btn.getAttribute('data-edit-id'));
                const user = users.find(x => x.id === id);
                if (!user) return;
                editingUserId = id;
                modalName.value = user.name || '';
                modalEmail.value = user.email || '';
                modalPassword.value = '';
                modalRole.value = user.role || 'user';
                openModal('Edit Pengguna');
            });
        });
        tbody.querySelectorAll('[data-delete-id]').forEach(btn => {
            btn.addEventListener('click', async () => {
                const id = Number(btn.getAttribute('data-delete-id'));
                if (!confirm('Hapus pengguna ini?')) return;
                try {
                    const res = await apiFetch(`/api/admin/users/${id}`, { method: 'DELETE' });
                    if (!res.ok) throw new Error('Gagal menghapus');
                    showToast('Pengguna dihapus');
                    await loadUsers();
                } catch (e) { showToast(e.message); }
            });
        });
    }
    function applyFilter() {
        const q = (searchInput.value || '').toLowerCase();
        const role = roleFilter.value || '';
        filtered = users.filter(u => {
            const matchText = (u.name || '').toLowerCase().includes(q) || (u.email || '').toLowerCase().includes(q);
            const matchRole = role ? u.role === role : true;
            return matchText && matchRole;
        });
        sortFiltered();
        page = 1;
        renderTable();
    }

    function sortFiltered() {
        filtered.sort((a, b) => {
            const va = (a[sortKey] || '').toString().toLowerCase();
            const vb = (b[sortKey] || '').toString().toLowerCase();
            if (va < vb) return sortDir === 'asc' ? -1 : 1;
            if (va > vb) return sortDir === 'asc' ? 1 : -1;
            return 0;
        });
    }
    async function loadUsers() {
        try {
            if (loadingView) loadingView.hidden = false;
            const res = await apiFetch('/api/admin/users');
            if (!res.ok) throw new Error('Gagal memuat data');
            users = await res.json();
            filtered = users.slice();
            sortFiltered();
            renderStats();
            renderTable();
        } catch (e) {
            showToast(e.message);
            users = [];
            filtered = [];
            renderStats();
            renderTable();
        } finally {
            if (loadingView) loadingView.hidden = true;
        }
    }

    // events
    addBtn?.addEventListener('click', () => {
        editingUserId = null;
        openModal('Tambah Pengguna');
    });
    modal.querySelectorAll('[data-modal-close]').forEach(el => el.addEventListener('click', closeModal));
    searchInput?.addEventListener('input', applyFilter);
    roleFilter?.addEventListener('change', applyFilter);
    document.getElementById('prev-page')?.addEventListener('click', () => { if (page > 1) { page--; renderTable(); } });
    document.getElementById('next-page')?.addEventListener('click', () => {
        const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
        if (page < totalPages) { page++; renderTable(); }
    });

    // Empty state add button
    emptyAddBtn?.addEventListener('click', () => {
        editingUserId = null;
        openModal('Tambah Pengguna');
    });

    // Sorting headers
    const thName = document.querySelector('th[data-i18n="userName"]');
    const thEmail = document.querySelector('th[data-i18n="userEmail"]');
    const thRole = document.querySelector('th[data-i18n="userRole"]');
    [
        { el: thName, key: 'name' },
        { el: thEmail, key: 'email' },
        { el: thRole, key: 'role' },
    ].forEach(({ el, key }) => {
        if (!el) return;
        el.style.cursor = 'pointer';
        el.title = 'Klik untuk sort';
        el.addEventListener('click', () => {
            if (sortKey === key) {
                sortDir = sortDir === 'asc' ? 'desc' : 'asc';
            } else {
                sortKey = key;
                sortDir = 'asc';
            }
            sortFiltered();
            renderTable();
        });
    });

    modalSave?.addEventListener('click', async () => {
        const payload = {
            name: modalName.value.trim(),
            email: modalEmail.value.trim(),
            password: modalPassword.value.trim(),
            role: modalRole.value.trim() || 'user'
        };
        if (!payload.name || !payload.email || (!editingUserId && !payload.password)) {
            showToast('Lengkapi data wajib');
            return;
        }
        try {
            if (editingUserId) {
                const res = await apiFetch(`/api/admin/users/${editingUserId}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password: payload.password, role: payload.role }) });
                if (!res.ok) throw new Error('Gagal mengupdate');
                showToast('Pengguna diupdate');
            } else {
                const res = await apiFetch('/api/admin/users', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
                if (!res.ok) throw new Error('Gagal membuat pengguna');
                showToast('Pengguna dibuat');
            }
            closeModal();
            await loadUsers();
        } catch (e) { showToast(e.message); }
    });

    // init
    loadUsers();
});