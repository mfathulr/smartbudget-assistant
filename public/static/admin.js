// Professional Admin Panel: User Management with OCR control on edit
document.addEventListener('DOMContentLoaded', () => {
    const tbody = document.getElementById('users-tbody');
    const emptyState = document.getElementById('empty-state');
    const searchInput = document.getElementById('search-input');
    const roleFilter = document.getElementById('role-filter');
    const addBtn = document.getElementById('add-user-btn');
    const modal = document.getElementById('user-modal');
    const modalTitle = document.getElementById('modal-title');
    const modalName = document.getElementById('modal-name');
    const modalEmail = document.getElementById('modal-email');
    const modalPassword = document.getElementById('modal-password');
    const passwordGroup = document.getElementById('password-group');
    const passwordHint = document.getElementById('password-hint');
    const modalRole = document.getElementById('modal-role');
    const ocrSection = document.getElementById('ocr-section');
    const modalOcrEnabled = document.getElementById('modal-ocr-enabled');
    const modalSave = document.getElementById('modal-save');
    const toast = document.getElementById('toast');
    const confirmModal = document.getElementById('confirm-modal');
    const confirmTitle = document.getElementById('confirm-title');
    const confirmMessage = document.getElementById('confirm-message');
    const confirmDetails = document.getElementById('confirm-details');
    const confirmUserName = document.getElementById('confirm-user-name');
    const confirmUserEmail = document.getElementById('confirm-user-email');
    const confirmActionBtn = document.getElementById('confirm-action-btn');
    const exportBtn = document.getElementById('export-btn');
    const emptyAddBtn = document.getElementById('empty-add-user');

    let users = [];
    let filtered = [];
    let page = 1;
    const pageSize = 10;
    let editingUserId = null;
    let pendingDeleteId = null;

    function showToast(msg, type = 'info') {
        if (!toast) return;
        toast.textContent = msg;
        toast.className = `toast show ${type}`;
        setTimeout(() => toast.classList.remove('show'), 2500);
    }

    function openModal(title, isEdit = false) {
        modalTitle.textContent = title;
        
        // Show OCR section only in EDIT mode
        if (ocrSection) {
            ocrSection.style.display = isEdit ? 'flex' : 'none';
        }

        // Show/hide password field based on mode
        if (passwordGroup) {
            passwordGroup.style.display = isEdit ? 'none' : 'block';
            if (passwordHint) {
                passwordHint.style.display = isEdit ? 'none' : 'block';
            }
        }

        modal.classList.add('active');
        setTimeout(() => modalName?.focus(), 50);
    }

    function closeModal() {
        modal.classList.remove('active');
        editingUserId = null;
        modalName.value = '';
        modalEmail.value = '';
        modalPassword.value = '';
        modalRole.value = 'user';
        if (modalOcrEnabled) modalOcrEnabled.checked = false;
    }

    function openConfirmModal(userName, userEmail, userId) {
        pendingDeleteId = userId;
        confirmTitle.textContent = 'Confirm Deletion';
        confirmMessage.textContent = 'Are you sure you want to delete this user? This action cannot be undone.';
        confirmUserName.textContent = userName;
        confirmUserEmail.textContent = userEmail;
        confirmDetails.style.display = 'block';
        confirmModal.classList.add('active');
    }

    function closeConfirmModal() {
        confirmModal.classList.remove('active');
        pendingDeleteId = null;
    }

    function exportToCSV() {
        if (filtered.length === 0) {
            showToast('No users to export', 'error');
            return;
        }

        const headers = ['ID', 'Name', 'Email', 'Role', 'OCR Enabled', 'Created At'];
        const rows = filtered.map(u => [
            u.id,
            u.name,
            u.email,
            u.role,
            u.ocr_enabled ? 'Yes' : 'No',
            u.created_at ? new Date(u.created_at).toLocaleString() : 'N/A'
        ]);

        let csvContent = headers.join(',') + '\n';
        rows.forEach(row => {
            csvContent += row.map(cell => `"${cell}"`).join(',') + '\n';
        });

        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `users_export_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        showToast(`Exported ${filtered.length} users successfully`, 'success');
    }

    function formatDate(dateStr) {
        if (!dateStr) return 'N/A';
        const date = new Date(dateStr);
        const now = new Date();
        const diffTime = Math.abs(now - date);
        const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays === 0) return 'Today';
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return `${diffDays} days ago`;
        
        return date.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });
    }

    function renderTable() {
        tbody.innerHTML = '';
        
        if (filtered.length === 0) {
            emptyState.style.display = '';
            return;
        }
        emptyState.style.display = 'none';

        const start = (page - 1) * pageSize;
        const rows = filtered.slice(start, start + pageSize);

        for (const u of rows) {
            const tr = document.createElement('tr');
            
            const ocrBadge = u.ocr_enabled 
                ? '<span class="badge badge-ocr-yes"><i class="fas fa-check-circle"></i> Yes</span>'
                : '<span class="badge badge-ocr-no"><i class="fas fa-times-circle"></i> No</span>';
            
            let roleBadge = '<span class="badge badge-user"><i class="fas fa-user"></i> User</span>';
            if (u.role === 'admin') {
                roleBadge = '<span class="badge badge-admin"><i class="fas fa-shield-alt"></i> Admin</span>';
            } else if (u.role === 'premium') {
                roleBadge = '<span class="badge badge-premium"><i class="fas fa-crown"></i> Premium</span>';
            }

            const createdDate = formatDate(u.created_at);
            const createdFull = u.created_at ? new Date(u.created_at).toLocaleString() : 'N/A';

            tr.innerHTML = `
                <td>${u.id}</td>
                <td>
                    <div style="font-weight: 600; color: var(--text-primary, #111827);">${u.name}</div>
                    <div style="font-size: 12px; color: var(--text-tertiary, #9ca3af);">${u.email}</div>
                </td>
                <td>${roleBadge}</td>
                <td>${ocrBadge}</td>
                <td>
                    <div style="font-size: 13px; color: var(--text-secondary, #6b7280);" title="${createdFull}">
                        <i class="fas fa-calendar-plus" style="font-size: 11px; opacity: 0.7; margin-right: 4px;"></i>
                        ${createdDate}
                    </div>
                </td>
                <td>
                    <div class="actions-cell">
                        <button class="action-btn action-btn-edit" data-edit-id="${u.id}" title="Edit User" aria-label="Edit user ${u.name}">
                            <i class="fas fa-pen"></i>
                        </button>
                        <button class="action-btn action-btn-delete" data-delete-id="${u.id}" data-user-name="${u.name}" data-user-email="${u.email}" title="Delete User" aria-label="Delete user ${u.name}">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        }

        renderPagination();
        attachEventListeners();
    }

    function renderPagination() {
        const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
        const pageInfo = document.getElementById('page-info');
        if (pageInfo) pageInfo.textContent = `${page} / ${totalPages}`;

        const prevBtn = document.getElementById('prev-page');
        const nextBtn = document.getElementById('next-page');
        if (prevBtn) prevBtn.disabled = page <= 1;
        if (nextBtn) nextBtn.disabled = page >= totalPages;
    }

    function renderStats() {
        const total = users.length;
        const admins = users.filter(u => u.role === 'admin').length;
        const premium = users.filter(u => u.role === 'premium').length;
        const standard = users.filter(u => u.role === 'user').length;
        document.getElementById('statUsers').textContent = String(total);
        document.getElementById('statAdmins').textContent = String(admins);
        document.getElementById('statPremium').textContent = String(premium);
        document.getElementById('statStandard').textContent = String(standard);
    }

    function attachEventListeners() {
        // Edit buttons
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
                
                if (modalOcrEnabled) {
                    modalOcrEnabled.checked = user.ocr_enabled || false;
                }

                // Show user context in modal title
                const modalTitleText = `Edit User - ${user.name}`;
                openModal(modalTitleText, true); // true = edit mode
            });
        });

        // Delete buttons - open confirmation modal
        tbody.querySelectorAll('[data-delete-id]').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = Number(btn.getAttribute('data-delete-id'));
                const userName = btn.getAttribute('data-user-name');
                const userEmail = btn.getAttribute('data-user-email');
                openConfirmModal(userName, userEmail, id);
            });
        });
    }

    function applyFilter() {
        const q = (searchInput.value || '').toLowerCase();
        const role = roleFilter.value || '';

        filtered = users.filter(u => {
            const matchText = (u.name || '').toLowerCase().includes(q) || 
                            (u.email || '').toLowerCase().includes(q);
            const matchRole = role ? u.role === role : true;
            return matchText && matchRole;
        });

        page = 1;
        renderTable();
    }

    async function loadUsers() {
        try {
            const res = await apiFetch('/api/admin/users');
            if (!res.ok) throw new Error('Failed to load users');
            users = await res.json();
            filtered = users.slice();
            renderStats();
            renderTable();
        } catch (e) {
            showToast(e.message, 'error');
            users = [];
            filtered = [];
            renderStats();
            renderTable();
        }
    }

    // Events
    addBtn?.addEventListener('click', () => {
        editingUserId = null;
        modalName.value = '';
        modalEmail.value = '';
        modalPassword.value = '';
        modalRole.value = 'user';
        if (modalOcrEnabled) modalOcrEnabled.checked = false;
        openModal('Add New User', false); // false = create mode
    });

    modal.querySelectorAll('[data-modal-close]').forEach(el => {
        el.addEventListener('click', closeModal);
    });

    // Confirmation modal events
    confirmModal?.querySelectorAll('[data-confirm-close]').forEach(el => {
        el.addEventListener('click', closeConfirmModal);
    });

    confirmActionBtn?.addEventListener('click', async () => {
        if (!pendingDeleteId) return;
        
        try {
            const res = await apiFetch(`/api/admin/users/${pendingDeleteId}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Failed to delete user');
            showToast('User deleted successfully', 'success');
            closeConfirmModal();
            await loadUsers();
        } catch (e) {
            showToast(e.message, 'error');
            closeConfirmModal();
        }
    });

    // Export button
    exportBtn?.addEventListener('click', exportToCSV);

    // Empty state add button
    emptyAddBtn?.addEventListener('click', () => {
        editingUserId = null;
        modalName.value = '';
        modalEmail.value = '';
        modalPassword.value = '';
        modalRole.value = 'user';
        if (modalOcrEnabled) modalOcrEnabled.checked = false;
        openModal('Add New User', false);
    });

    searchInput?.addEventListener('input', applyFilter);
    roleFilter?.addEventListener('change', applyFilter);

    document.getElementById('prev-page')?.addEventListener('click', () => {
        if (page > 1) { page--; renderTable(); }
    });

    document.getElementById('next-page')?.addEventListener('click', () => {
        const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
        if (page < totalPages) { page++; renderTable(); }
    });

    // Save (Create/Edit)
    modalSave?.addEventListener('click', async () => {
        const payload = {
            name: modalName.value.trim(),
            email: modalEmail.value.trim(),
            role: modalRole.value.trim() || 'user',
        };

        // Add password only for create mode
        if (!editingUserId) {
            payload.password = modalPassword.value.trim();
        }

        // Add OCR status only for edit mode
        if (editingUserId && modalOcrEnabled) {
            payload.ocr_enabled = modalOcrEnabled.checked;
        }

        // Debug log
        console.log('[DEBUG] Payload being sent:', payload);

        // Validation
        if (!payload.name || !payload.email) {
            showToast('Name and email are required', 'error');
            return;
        }

        if (!editingUserId && !payload.password) {
            showToast('Password is required for new users', 'error');
            return;
        }

        if (!editingUserId && payload.password.length < 6) {
            showToast('Password must be at least 6 characters', 'error');
            return;
        }

        try {
            let res;
            if (editingUserId) {
                // Edit mode - PUT request
                res = await apiFetch(`/api/admin/users/${editingUserId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (!res.ok) {
                    const errData = await res.json();
                    throw new Error(errData.error || 'Failed to update user');
                }
                showToast('User updated successfully', 'success');
            } else {
                // Create mode - POST request
                res = await apiFetch('/api/admin/users', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (!res.ok) {
                    const errData = await res.json();
                    console.error('[ERROR] Create user failed:', res.status, errData);
                    throw new Error(errData.error || 'Failed to create user');
                }
                showToast('User created successfully', 'success');
            }
            closeModal();
            await loadUsers();
        } catch (e) {
            showToast(e.message, 'error');
        }
    });

    // Init
    loadUsers();
});