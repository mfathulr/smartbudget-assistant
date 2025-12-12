document.addEventListener('DOMContentLoaded', () => {
    // Tidak ada lagi pemanggilan data di sini.
    // Semua akan diinisiasi oleh app.js.
    setupEventListeners();
    loadProfileStats();
});

/**
 * Fungsi ini sekarang dipanggil oleh app.js setelah data pengguna tersedia.
 * Ini adalah satu-satunya cara data masuk ke halaman profil.
 * @param {object} user - Objek pengguna yang sudah dimuat.
 */
function loadProfileData(user) {
    if (user) {
        updateProfileUI(user);
    } else {
        const err = new Error('Data pengguna tidak tersedia dari app.js');
        console.error('Failed to load user info:', err);
        showMessage('profile-message', 'Gagal memuat data profil.', 'error');
    }
}

function updateProfileUI(user) {
    // Fungsi ini sekarang selalu menerima objek user yang bersih.

    if (!user || !user.name) {
        console.error("Data pengguna tidak valid diterima oleh updateProfileUI", user);
        return;
    }

    // Isi elemen di header profil
    document.getElementById('user-name-display').textContent = user.name || 'Nama Belum Diatur';
    document.getElementById('user-email-display').textContent = user.email;

    const roleDisplay = document.getElementById('user-role-display');
    if (user.role) {
        let roleText = user.role.charAt(0).toUpperCase() + user.role.slice(1);
        let roleIcon = '👤';
        let roleClass = '';
        
        if (user.role === 'admin') {
            roleIcon = '🛡️';
            roleClass = 'role-admin';
        } else if (user.role === 'premium') {
            roleIcon = '👑';
            roleClass = 'role-premium';
            roleText = 'Premium';
        } else {
            roleClass = 'role-user';
        }
        
        roleDisplay.textContent = `${roleIcon} ${roleText}`;
        roleDisplay.className = `profile-role ${roleClass}`;
        roleDisplay.style.display = 'inline-block';
    }

    // Update avatar display
    const avatarDisplay = document.getElementById('avatar-display');
    
    if (user.avatar_url) {
        avatarDisplay.innerHTML = `<img src="${user.avatar_url}" alt="Avatar">`;
    } else {
        // Show initial from name
        const initial = user.name ? user.name.charAt(0).toUpperCase() : 'U';
        avatarDisplay.innerHTML = `<div class="avatar-initial">${initial}</div>`;
    }

    // Populate form fields in the main content
    document.getElementById('profile-name').value = user.name || '';
    document.getElementById('profile-email').value = user.email;
    document.getElementById('profile-phone').value = user.phone || '';
    document.getElementById('profile-bio').value = user.bio || '';
}

function setupEventListeners() {
    // Profile info form
    document.getElementById('profile-form').addEventListener('submit', handleProfileUpdate);

    // Password change form
    document.getElementById('password-form').addEventListener('submit', handlePasswordChange);
    
    // Avatar upload
    document.getElementById('avatar-input').addEventListener('change', handleAvatarUpload);
}

async function handleAvatarUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    // Validate file type
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
        alert('Format file tidak didukung. Gunakan JPG, PNG, atau WebP.');
        return;
    }
    
    // Validate file size (max 2MB)
    if (file.size > 2 * 1024 * 1024) {
        alert('Ukuran file terlalu besar. Maksimal 2MB.');
        return;
    }
    
    // Show preview immediately
    const reader = new FileReader();
    reader.onload = (event) => {
        const avatarDisplay = document.getElementById('avatar-display');
        avatarDisplay.innerHTML = `<img src="${event.target.result}" alt="Avatar Preview">`;
    };
    reader.readAsDataURL(file);
    
    // Upload to server
    const formData = new FormData();
    formData.append('avatar', file);
    
    try {
        // Use apiFetch but pass FormData directly (don't set Content-Type header)
        const res = await apiFetch('/api/me/avatar', {
            method: 'POST',
            body: formData
        });
        
        const data = await res.json();
        console.log('Avatar uploaded successfully:', data);
        
        // Show success message
        const messageEl = document.getElementById('profile-message');
        showMessage(messageEl, '✅ Avatar berhasil diupload!', 'success');
        
        // Update user info if returned
        if (data.user) {
            updateProfileUI(data.user);
            
            // Reload user menu to show new avatar
            if (typeof loadUserMenu === 'function') {
                await loadUserMenu();
            }
        }
    } catch (err) {
        console.error('Avatar upload error:', err);
        const errorMessage = err.message || 'Terjadi kesalahan saat upload avatar';
        alert('Gagal upload avatar: ' + errorMessage);
        // Reload current avatar or show initial
        try {
            const currentUserRes = await apiFetch('/api/me');
            const currentUser = await currentUserRes.json();
            updateProfileUI(currentUser);
        } catch (reloadErr) {
            console.error('Failed to reload profile:', reloadErr);
        }
    }
}

async function loadProfileStats() {
    try {
        // Fetch accounts for balance
        const accountsRes = await apiFetch('/api/accounts');
        const accountsData = await accountsRes.json();
        const totalBalance = accountsData.total_all || 0;
        
        // Fetch transactions count
        const transactionsRes = await apiFetch('/api/transactions');
        const transactions = await transactionsRes.json();
        const transactionCount = transactions.length;
        
        // Fetch savings goals count
        const savingsRes = await apiFetch('/api/savings');
        const savings = await savingsRes.json();
        const goalsCount = savings.length;
        
        // Update UI
        document.getElementById('stat-balance').textContent = formatCurrency(totalBalance);
        document.getElementById('stat-transactions').textContent = transactionCount;
        document.getElementById('stat-goals').textContent = goalsCount;
    } catch (err) {
        console.error('Failed to load stats:', err);
    }
}

// Utility function for currency formatting
function formatCurrency(num) {
    if (num === null || num === undefined) return "Rp 0";
    return "Rp " + Math.round(num).toLocaleString("id-ID");
}

async function handleProfileUpdate(e) {
    e.preventDefault();
    const messageEl = document.getElementById('profile-message');
    showMessage(messageEl, 'Menyimpan...', 'info');

    const payload = {
        name: document.getElementById('profile-name').value,
        phone: document.getElementById('profile-phone').value,
        bio: document.getElementById('profile-bio').value,
    };

    try {
        const res = await apiFetch('/api/me/profile', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Gagal menyimpan profil.');
        
        showMessage(messageEl, 'Profil berhasil diperbarui!', 'success');
        // Gunakan data user yang baru dari backend untuk memperbarui seluruh UI
        updateProfileUI(data.user); // Endpoint profile mengembalikan data di dalam properti 'user'
    } catch (err) {
        showMessage(messageEl, err.message, 'error');
    }
}

async function handlePasswordChange(e) {
    e.preventDefault();
    const messageEl = document.getElementById('password-message');
    const currentPassword = document.getElementById('current-password').value;
    const newPassword = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;

    if (!currentPassword || !newPassword) {
        return showMessage(messageEl, 'Semua field password harus diisi.', 'error');
    }
    if (newPassword.length < 6) {
        return showMessage(messageEl, 'Password minimal harus 6 karakter.', 'error');
    }
    if (newPassword !== confirmPassword) {
        return showMessage(messageEl, 'Password baru dan konfirmasi tidak cocok.', 'error');
    }

    try {
        const res = await apiFetch('/api/me/password', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ current_password: currentPassword, password: newPassword })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Gagal mengubah password.');
        
        showMessage(messageEl, 'Password berhasil diubah!', 'success');
        e.target.reset();
    } catch (err) {
        showMessage(messageEl, err.message, 'error');
    }
}

function showMessage(elementOrId, text, type) {
    const messageEl = typeof elementOrId === 'string' ? document.getElementById(elementOrId) : elementOrId;
    if (!messageEl) return;
    messageEl.textContent = text;
    
    // Map our types to the main stylesheet's classes
    let className = 'small ';
    if (type === 'success') className += 'success';
    else if (type === 'error') className += 'error';
    else className += 'info'; // 'info' can be a generic message style

    messageEl.className = className;
    messageEl.style.display = 'block';

    // Hide message after 5 seconds
    setTimeout(() => {
        if (messageEl.textContent === text) { // Only hide if message hasn't changed
            messageEl.style.display = 'none';
        }
    }, 5000);
}