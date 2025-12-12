// ============================================
//   THEME MANAGEMENT
// ============================================

// Initialize theme on page load (before DOMContentLoaded)
(function initTheme() {
  const savedTheme = localStorage.getItem('theme') || 'auto';
  
  function applyTheme(theme) {
    if (theme === 'auto') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      document.documentElement.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
    } else {
      document.documentElement.setAttribute('data-theme', theme);
    }
  }
  
  // Apply immediately to prevent flash
  applyTheme(savedTheme);
  
  // Listen for system theme changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (localStorage.getItem('theme') === 'auto') {
      applyTheme('auto');
    }
  });
})();

// ============================================
//   UTILITY FUNCTIONS
// ============================================

// Utility: format numbers as Indonesian Rupiah strings
function formatCurrency(num) {
  if (num === null || num === undefined) return "Rp 0";
  return "Rp " + Math.round(num).toLocaleString("id-ID");
}

// Utility: parse amount input (remove comma separator)
function parseAmount(valueStr) {
  if (!valueStr) return 0;
  // Remove comma separator and convert to float
  return parseFloat(String(valueStr).replace(/,/g, ""));
}

// Utility: debounce function to reduce function call frequency
function debounce(func, delay) {
  let timeoutId;
  return function(...args) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func.apply(this, args), delay);
  };
}

// Utility: throttle function to limit function call frequency
function throttle(func, limit) {
  let inThrottle;
  return function(...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

// Utility: show notification toast
function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 12px 20px;
    background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
    color: white;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 10000;
    font-size: 14px;
    font-weight: 500;
    animation: slideInRight 0.3s ease;
  `;
  notification.textContent = message;
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.style.animation = 'slideOutRight 0.3s ease';
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

// Helper: fetch dengan session token (dibuat global)
async function apiFetch(url, options = {}) {
  const token = localStorage.getItem('session_token');
  if (!token) {
    // Redirect to login if no token
    window.location.href = '/login.html';
    throw new Error('No session token');
  }

  const headers = { ...options.headers };
  headers['Authorization'] = `Bearer ${token}`;
  headers['Cache-Control'] = 'no-cache, no-store, must-revalidate';
  headers['Pragma'] = 'no-cache';
  headers['Expires'] = '0';

  const response = await fetch(url, { ...options, headers, cache: 'no-store' });

  // Check jika unauthorized
  if (response.status === 401) {
    localStorage.removeItem('session_token');
    window.location.href = '/login.html';
    throw new Error('Session expired');
  }

  return response;
}

// Logout handler (dibuat global)
async function handleLogout() {
  try {
    const token = localStorage.getItem('session_token');
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    await fetch('/api/logout', {
      method: 'POST',
      headers,
    });
  } catch (e) {
    console.error('Logout API call failed, proceeding with client-side cleanup.', e);
  } finally {
    // Selalu hapus token di sisi klien, apapun respons server
    localStorage.removeItem('session_token');
    document.cookie = 'session_token=; path=/; max-age=0';
    window.location.href = '/login.html';
  }
}

function renderGuestLoginLink() {
  const container = document.getElementById('user-menu-container');
  if (!container) return;
  container.innerHTML = `
    <a href="/login.html" class="guest-login-link">
      <i class="fas fa-sign-in-alt"></i>
      Masuk
    </a>
  `;
}

/**
 * Load and render user menu - can be called to refresh avatar
 */
async function loadUserMenu() {
  const userMenuContainer = document.getElementById('user-menu-container');
  if (!userMenuContainer) return;
  
  try {
    if (!localStorage.getItem('session_token')) {
      renderGuestLoginLink();
      return;
    }
    
    userMenuContainer.innerHTML = '';
    const userResponse = await apiFetch('/api/me');
    if (!userResponse.ok) throw new Error('Failed');
    const user = await userResponse.json();

    let adminLink = '';
    if (user && user.role === 'admin') {
      adminLink = `<a href="/admin.html" class="user-menu-item" data-i18n="menuAdmin">Panel Admin</a>`;
    }

    const avatarHTML = user.avatar_url 
      ? `<img src="${user.avatar_url}" alt="Avatar" class="user-avatar-img">`
      : `<div class="user-avatar-initial">${user.name ? user.name.charAt(0).toUpperCase() : user.email.charAt(0).toUpperCase()}</div>`;
    
    userMenuContainer.innerHTML = `
      <div class="user-menu">
        <button class="user-menu-trigger">
          <div class="user-avatar-menu">${avatarHTML}</div>
          <span class="user-email">${user.email}</span>
          <i class="fas fa-chevron-down" style="font-size: 0.8em;"></i>
        </button>
        <div class="user-menu-dropdown">
          <a href="/" class="user-menu-item" data-i18n="menuDashboard">Dashboard</a>
          <div class="user-menu-divider"></div>
          <a href="/profile.html" class="user-menu-item" data-i18n="menuProfile">Profil</a>
          <a href="/settings.html" class="user-menu-item" data-i18n="menuSettings">Pengaturan</a>
          ${adminLink}
          <div class="user-menu-divider"></div>
          <a href="#" id="logout-link" class="user-menu-item" data-i18n="menuLogout">Logout</a>
        </div>
      </div>
    `;

    userMenuContainer.querySelector('.user-menu-trigger')?.addEventListener('click', (e) => {
      e.stopPropagation();
      userMenuContainer.querySelector('.user-menu-dropdown')?.classList.toggle('active');
    });
    
    userMenuContainer.querySelector('#logout-link')?.addEventListener('click', (e) => {
      e.preventDefault();
      handleLogout();
    });
    
    const currentLang = localStorage.getItem('language') || 'id';
    setLanguage(currentLang);
    
    return user;
  } catch (err) {
    console.error('Failed to load user menu:', err);
    renderGuestLoginLink();
  }
}

window.loadUserMenu = loadUserMenu;

/**
 * Fungsi utama yang berjalan saat halaman dimuat.
 * Menggabungkan semua logika DOMContentLoaded.
 */
document.addEventListener('DOMContentLoaded', async () => {
  // Flag untuk memastikan listener window hanya ditambahkan sekali
  let isWindowClickListenerAdded = false;

  const token = localStorage.getItem('session_token');
  
  // Jika tidak ada token dan kita di halaman utama, langsung ke login.
  // Untuk halaman lain, decorator @require_login di backend yang akan menangani.
  if (!token && window.location.pathname === '/') {
    window.location.href = '/login.html';
    return; // Hentikan eksekusi lebih lanjut
  }

  const userMenuContainer = document.getElementById('user-menu-container');
  const headerEl = document.querySelector('header');
  // Enhance header shadow on scroll
  if (headerEl) {
    const onScroll = () => {
      if (window.scrollY > 4) headerEl.classList.add('header-scrolled');
      else headerEl.classList.remove('header-scrolled');
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // Initialize language switcher on all pages
  const savedLang = localStorage.getItem('language') || 'id';
  setLanguage(savedLang);
  const langIdBtn = document.getElementById('lang-id');
  const langEnBtn = document.getElementById('lang-en');
  if (langIdBtn) langIdBtn.addEventListener('click', () => setLanguage('id'));
  if (langEnBtn) langEnBtn.addEventListener('click', () => setLanguage('en'));
  console.log('User menu container found:', userMenuContainer);
  console.log('Session token exists:', !!localStorage.getItem('session_token'));

  // Render user menu
  // Load user menu and get user data
  const user = await loadUserMenu();

  // Add active page badge next to title (skip auth pages)
  const titleEl = document.querySelector('header h1');
  if (titleEl) {
    const path = window.location.pathname;
    const isAuthPage = path.includes('login') || path.includes('forgot') || path.includes('reset');
    if (!isAuthPage) {
      let page = 'Dashboard';
      if (path.includes('admin')) page = 'Admin';
      else if (path.includes('profile')) page = 'Profile';
      else if (path.includes('settings')) page = 'Settings';
      const badge = document.createElement('span');
      badge.className = 'page-badge';
      badge.textContent = page;
      titleEl.appendChild(badge);
    }
  }
  
  // Add window click listener to close dropdown
  if (!isWindowClickListenerAdded) {
    window.addEventListener('click', (e) => {
      const activeDropdown = document.querySelector('.user-menu-dropdown.active');
      if (activeDropdown && !activeDropdown.closest('.user-menu').contains(e.target)) {
        activeDropdown.classList.remove('active');
      }
    });
    isWindowClickListenerAdded = true;
  }

  // If on profile page, load profile data with user info
  if (user && typeof loadProfileData === 'function') {
    loadProfileData(user);
  }

  // Initialize chat model dropdown to reflect saved provider & models (global scope)
  window.chatProvider = 'google';
  window.chatModel = 'gemini-2.0-flash-lite';
  window.chatModelDefinitions = {
    google: [
      { id: 'gemini-2.5-flash-lite', label: 'Gemini 2.5 Flash Lite', premium: false },
      { id: 'gemini-2.5-flash', label: 'Gemini 2.5 Flash', premium: false },
      { id: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro', premium: true },
    ],
    openai: [
      { id: 'gpt-4o-mini', label: 'GPT-4o Mini', premium: false },
      { id: 'gpt-5-nano', label: 'GPT-5 Nano', premium: true },
      { id: 'gpt-5-mini', label: 'GPT-5 Mini', premium: true },
      { id: 'gpt-5', label: 'GPT-5', premium: true },
    ],
  };

  const defaultChatModelFor = (provider) => {
    const list = window.chatModelDefinitions[provider] || [];
    return list.length ? list[0].id : null;
  };

  const populateModelSelect = (provider, currentModel, userRole = 'user') => {
    const modelSelect = document.getElementById('model-provider');
    if (!modelSelect) {
      console.warn('[ADVISOR] Model dropdown not found in DOM');
      return false;
    }
    console.log('[ADVISOR] Populating dropdown for provider:', provider, 'with', window.chatModelDefinitions[provider]?.length, 'models', 'User role:', userRole);
    modelSelect.innerHTML = '';
    (window.chatModelDefinitions[provider] || []).forEach((m) => {
      const opt = document.createElement('option');
      opt.value = m.id;
      
      // Add premium badge and disable for standard users
      if (m.premium && userRole === 'user') {
        opt.textContent = `${m.label} 👑 (Premium)`;
        opt.disabled = true;
        opt.style.color = '#999';
      } else if (m.premium) {
        opt.textContent = `${m.label} 👑`;
      } else {
        opt.textContent = m.label;
      }
      
      modelSelect.appendChild(opt);
    });
    
    // Set current model, but check if it's premium and user is standard
    let selectedModel = currentModel || defaultChatModelFor(provider);
    const selectedModelDef = (window.chatModelDefinitions[provider] || []).find(m => m.id === selectedModel);
    
    // If selected model is premium and user is standard, switch to default non-premium model
    if (selectedModelDef && selectedModelDef.premium && userRole === 'user') {
      console.warn('[ADVISOR] Selected model is premium but user is standard, switching to default');
      selectedModel = (window.chatModelDefinitions[provider] || []).find(m => !m.premium)?.id || defaultChatModelFor(provider);
    }
    
    modelSelect.value = selectedModel;
    console.log('[ADVISOR] Dropdown populated, selected:', modelSelect.value, 'total options:', modelSelect.options.length);
    return true;
  };

  // Make it globally accessible
  window.populateModelSelect = populateModelSelect;
  window.defaultChatModelFor = defaultChatModelFor;

  // Store user settings globally for later initialization
  if (user) {
    let savedProvider = user.ai_provider || 'google';
    let savedModel = user.ai_model || defaultChatModelFor(savedProvider);

    // Use saved settings from database (backend validates role restrictions)
    window.chatProvider = savedProvider;
    window.chatModel = savedModel || defaultChatModelFor(window.chatProvider);
    window.userRole = user.role || 'user'; // Store user role globally
    localStorage.setItem('model_provider', window.chatProvider);
    localStorage.setItem('model', window.chatModel);
    console.log('[ADVISOR INIT] Provider:', window.chatProvider, 'Model:', window.chatModel, 'User Role:', window.userRole);

    // Try to populate dropdown now (if on dashboard)
    const modelSelect = document.getElementById('model-provider');
    if (modelSelect) {
      // Show info based on role
      if (user.role === 'user' && savedProvider === 'openai') {
        modelSelect.title = '⚠️ OpenAI is Premium only. Your requests will be blocked by server.';
      } else if (user.role === 'user') {
        modelSelect.title = 'Standard users: Premium models (👑) require upgrade. Note: Free tier models may have quota limits.';
      } else {
        modelSelect.title = 'Choose your preferred AI model. Note: Free tier models may have quota limits.';
      }
      
      populateModelSelect(window.chatProvider, window.chatModel, window.userRole);

      // Listen for model change (provider is fixed by settings)
      modelSelect.addEventListener('change', () => {
        window.chatModel = modelSelect.value;
        localStorage.setItem('model', window.chatModel);
        console.log('[ADVISOR] Model changed to:', window.chatModel);
      });
    } else {
      // Dropdown will be populated when tab is activated
      console.log('[ADVISOR] Dropdown not yet in DOM, will populate on tab activation');
    }
  }

  // Hide old admin link if exists
  const oldAdminLink = document.getElementById('admin-link');
  if (oldAdminLink) {
    oldAdminLink.style.display = 'none';
  }

    // Panggil init() hanya jika kita berada di halaman utama (dashboard).
    // Ini akan mencegah error JavaScript di halaman lain seperti profile.html atau settings.html
    if (window.location.pathname === '/' || window.location.pathname === '/index.html') {
      await init();
    }
});

const translations = {
  id: {
    // App branding
    appTitle: "SmartBudget Assistant",
    brandTitle: "SmartBudget Assistant",
    loginSubtitle: "SmartBudget Assistant",
    totalBalanceLabel: "💰 Saldo Total",
    accountFilterLabel: "Akun:",
    allAccountsOption: "Semua Akun",
    savingsGoalsLabel: "🎯 Target Tabungan",
    collectedLabel: "Terkumpul",
    summaryTab: "Ringkasan",
    transactionsTab: "Transaksi",
    savingsTab: "Tabungan",
    advisorTab: "Advisor",
    monthlySummaryTitle: "Ringkasan Bulan Ini",
    thisMonthLabel: "Bulan ini",
    incomeLabel: "Pemasukan",
    expenseLabel: "Pengeluaran",
    netBalanceLabel: "Saldo Bersih",
    differenceLabel: "Selisih",
    expenseByCategoryTitle: "Pengeluaran Per Kategori",
    accountBalanceTitle: "Distribusi Saldo Akun",
    noExpenseData: "Belum ada data pengeluaran",
    noAccountData: "Belum ada data akun",
    categoryBreakdownTitle: "Rincian Per Kategori",
    allCategories: "Semua",
    expenseOnly: "Pengeluaran",
    incomeOnly: "Pemasukan",
    percentageColumn: "Persentase",
    accountBalancesTitle: "Saldo Per Akun",
    byCategoryTitle: "Per Kategori",
    categoryColumn: "Kategori",
    incomeColumn: "Pemasukan",
    expenseColumn: "Pengeluaran",
    byAccountTitle: "Saldo Per Akun",
    accountColumn: "Akun",
    balanceColumn: "Saldo",
    addTransactionSubTab: "Tambah Transaksi",
    fundTransferSubTab: "Pemindahan Dana",
    historySubTab: "Riwayat Transaksi",
    addTransactionTitle: "Tambah Transaksi",
    dateLabel: "Tanggal",
    typeLabel: "Tipe",
    expenseOption: "Pengeluaran",
    incomeOption: "Pemasukan",
    categoryLabel: "Kategori",
    amountLabel: "Jumlah",
    descriptionLabel: "Deskripsi",
    saveTransactionButton: "Simpan Transaksi",
    fundTransferTitle: "Pemindahan Dana",
    fromAccountLabel: "Dari Akun",
    toAccountLabel: "Ke Akun",
    selectSavingsGoalLabel: "Pilih Target Tabungan",
    descriptionOptionalLabel: "Deskripsi (opsional)",
    transferFundButton: "Pindahkan Dana",
    transactionHistoryTitle: "Riwayat Transaksi",
    startDateLabel: "Dari Tanggal",
    endDateLabel: "Sampai Tanggal",
    searchDescriptionLabel: "Cari Deskripsi",
    applyFilterButton: "Terapkan",
    resetFilterButton: "Reset",
    actionsColumn: "Aksi",
    savingsGoalsTitle: "Tujuan Tabungan",
    savingsGoalInfo: "💡 Tetapkan target tabungan Anda dan lacak progress setiap bulannya",
    goalNameLabel: "Nama Target",
    targetAmountLabel: "Target Amount (Rp)",
    targetDateLabel: "Tanggal Target",
    addGoalButton: "Tambah Target",
    newChatButton: "Obrolan Baru",
    chatHistoryHeader: "Riwayat Obrolan",
    welcomeToAdvisor: "Selamat Datang di Advisor AI",
    welcomeToAdvisorDesc: "SmartBudget Assistant Anda. Mulai percakapan untuk mendapatkan saran finansial.",
    chatPlaceholder: "Ketik pesan Anda...",
    aiDisclaimer: "AI dapat membuat kesalahan. Verifikasi informasi penting.",
    featureFinancialAnalysis: "Analisis Keuangan",
    featureSavingsAdvice: "Saran Tabungan",
    featureBudgetManagement: "Kelola Budget",
    typingIndicator: "AI sedang mengetik…",
    // Login page keys
    loginTitle: "Login",
    emailLabel: "Email/Username",
    passwordLabel: "Password",
    loginButton: "Masuk",
    dontHaveAccount: "Belum punya akun?",
    registerLink: "Daftar di sini",
    // Register page keys
    registerTitle: "Daftar",
    registerSubtitle: "Buat akun baru",
    fullNameLabel: "Nama Lengkap",
    registerButton: "Daftar",
    alreadyHaveAccount: "Sudah punya akun?",
    loginLinkText: "Login di sini",
    registrationSuccess: "Pendaftaran berhasil! Mengalihkan ke login...",
    emailAlreadyExists: "Email sudah terdaftar",
    registrationFailed: "Pendaftaran gagal",
    passwordWeak: "Lemah",
    passwordFair: "Sedang",
    passwordStrong: "Kuat",
    passwordStrengthLabel: "Kekuatan",
    agreeTermsLabel: "Saya setuju dengan <a href=\"/terms.html\" target=\"_blank\">Syarat & Ketentuan</a> dan <a href=\"/privacy.html\" target=\"_blank\">Kebijakan Privasi</a>",
    agreeTermsPrefix: "Saya setuju dengan",
    termsLink: "Syarat & Ketentuan",
    termsTitle: "Syarat & Ketentuan",
    agreeTermsAnd: "dan",
    privacyLink: "Kebijakan Privasi",
    privacyTitle: "Kebijakan Privasi",
    termsModalTitle: "Syarat & Ketentuan",
    privacyModalTitle: "Kebijakan Privasi",
    termsRequired: "Anda harus menyetujui Syarat & Ketentuan",
    // OTP Verification
    otpModalTitle: "Verifikasi Email",
    otpSentMessage: "Kami telah mengirim kode verifikasi ke email Anda",
    otpCodeLabel: "Kode Verifikasi (6 digit)",
    verifyButton: "Verifikasi",
    resendOtpButton: "Kirim Ulang",
    otpNotReceived: "Tidak menerima kode?",
    otpVerifyingMessage: "Memverifikasi kode...",
    otpInvalidError: "Kode OTP tidak valid",
    otpExpiredError: "Kode OTP telah kedaluwarsa",
    generatePassword: "Buat Password Kuat",
    generatePasswordHint: "Butuh password yang kuat?",
    passwordCopied: "Password disalin ke clipboard!",
    otpVerificationSuccess: "Verifikasi berhasil! Akun Anda telah dibuat.",
    sendingOtp: "Mengirim kode verifikasi...",
    otpSentSuccess: "Kode verifikasi telah dikirim ke email Anda",
    loginSuccess: "Login berhasil! Mengalihkan...",
    invalidEmail: "Email atau username tidak valid",
    invalidPassword: "Password tidak valid",
    loginFailed: "Login gagal",
    errorOccurred: "Terjadi kesalahan",
    rememberMe: "Ingat saya",
    forgotPassword: "Lupa password?",
    recaptchaNoticeHtml: "Situs ini dilindungi oleh reCAPTCHA dan <a href=\"https://policies.google.com/privacy\" target=\"_blank\" rel=\"noopener noreferrer\">Kebijakan Privasi</a> serta <a href=\"https://policies.google.com/terms\" target=\"_blank\" rel=\"noopener noreferrer\">Persyaratan Layanan</a> Google berlaku.",
    recaptchaNotice: "Situs ini dilindungi oleh reCAPTCHA dan Kebijakan Privasi serta Persyaratan Layanan Google berlaku.",
    brandTagline: "Pendamping Keuangan Anda",
    brandSubtitle: "Kelola keuangan dengan cerdas dan terstruktur.",
    featureTransactions: "Pencatatan transaksi harian",
    featureSavings: "Target tabungan dan progress",
    featureSummary: "Ringkasan dan analisis bulanan",
    welcomeToSmartBudget: "Bergabung dengan SmartBudget",
    registerWelcomeMessage: "Mulai perjalanan finansial Anda bersama SmartBudget Assistant. Kelola keuangan dengan mudah dan capai tujuan finansial Anda.",
    feature1: "Kelola Keuangan dengan Mudah",
    feature2: "Analisis Keuangan dengan AI",
    feature3: "Capai Target Tabungan Anda",
    feature4: "Data Aman & Terenkripsi",
    // Forgot Password page
    forgotPasswordTitle: "Lupa Password",
    forgotPasswordDesc: "Masukkan email Anda. Jika terdaftar, kami akan kirim tautan reset.",
    sendResetLink: "Kirim Tautan Reset",
    backToLogin: "Kembali ke Login",
    resetLinkSent: "Jika email terdaftar, link reset telah dikirim.",
    requestFailed: "Gagal memproses permintaan",
    networkError: "Terjadi kesalahan jaringan",
    devModeNotice: "Mode Pengujian:",
    smtpNotConfigured: "SMTP belum dikonfigurasi. Gunakan tautan berikut:",
    // Reset Password page
    resetPasswordTitle: "Reset Password",
    resetPasswordDesc: "Masukkan password baru Anda.",
    newPasswordLabel: "Password Baru",
    confirmPasswordLabel: "Konfirmasi Password",
    resetPasswordButton: "Reset Password",
    tokenNotFound: "Token tidak ditemukan. Buka tautan reset dari email.",
    passwordMismatch: "Password tidak cocok",
    passwordTooShort: "Password minimal 6 karakter",
    passwordResetSuccess: "Password berhasil direset. Mengalihkan ke login...",
    passwordResetFailed: "Gagal mereset password",
    // Password reset API messages
    emailRequired: "Email harus diisi",
    resetLinkSentIfRegistered: "Jika email terdaftar, link reset telah dikirim.",
    tokenAndPasswordRequired: "Token dan password baru wajib diisi",
    passwordMinLength: "Password minimal 6 karakter",
    invalidToken: "Token tidak valid",
    tokenExpired: "Token sudah kadaluarsa",
    passwordResetSuccessLogin: "Password berhasil direset. Silakan login.",
    passwordResetError: "Gagal mereset password",
    // Profile page
    profileTitle: "Informasi Profil",
    profileName: "Nama",
    profilePhone: "Nomor Telepon",
    profileEmail: "Email",
    profileBio: "Bio Singkat",
    saveInfo: "Simpan Informasi",
    changePasswordTitle: "Ubah Password",
    currentPassword: "Password Saat Ini",
    newPassword: "Password Baru",
    confirmPassword: "Konfirmasi Password Baru",
    savePassword: "Simpan Password",
    // Settings page
    settingsTitle: "Pengaturan",
    settingsDesc: "Sesuaikan preferensi dan pengaturan aplikasi Anda",
    languageTitle: "Bahasa",
    languageDesc: "Pilih bahasa antarmuka aplikasi",
    themeTitle: "Tema",
    themeDesc: "Pilih tema tampilan aplikasi",
    themeLight: "Terang",
    themeDark: "Gelap",
    themeAuto: "Otomatis",
    autoLogoutTitle: "Auto-Logout Timer",
    autoLogoutDesc: "Otomatis logout setelah tidak aktif untuk meningkatkan keamanan",
    minutesLabel: "menit",
    saveButton: "Simpan Pengaturan",
    saveSuccess: "Pengaturan berhasil disimpan!",
    deleteAccountTitle: "Hapus Akun",
    deleteAccountDesc: "⚠️ Tindakan ini tidak dapat dibatalkan. Semua data Anda akan dihapus secara permanen.",
    deleteAccountBtn: "Hapus Akun Saya",
    confirmDeleteTitle: "Konfirmasi Hapus Akun",
    confirmDeleteWarning: "⚠️ Anda akan menghapus akun secara permanen. Semua transaksi, tabungan, dan data lainnya akan hilang.",
    enterPasswordConfirm: "Masukkan password untuk konfirmasi:",
    understandDelete: "Saya memahami bahwa tindakan ini tidak dapat dibatalkan",
    cancelBtn: "Batal",
    confirmDeleteBtn: "Hapus Akun",
    // Admin page
    userManagement: "Manajemen Pengguna",
    addUser: "Tambah Pengguna",
    userId: "ID",
    userName: "Nama",
    userEmail: "Email",
    userRole: "Role",
    actions: "Aksi",
    addNewUser: "Tambah Pengguna Baru",
    cancel: "Batal",
    save: "Simpan",
    resetPassword: "Reset Password",
    // User menu
    menuDashboard: "Dashboard",
    menuProfile: "Profil",
    menuSettings: "Pengaturan",
    menuAdmin: "Panel Admin",
    menuLogout: "Keluar",
  },
  en: {
    // App branding
    appTitle: "SmartBudget Assistant",
    brandTitle: "SmartBudget Assistant",
    loginSubtitle: "SmartBudget Assistant",
    totalBalanceLabel: "💰 Total Balance",
    accountFilterLabel: "Account:",
    allAccountsOption: "All Accounts",
    savingsGoalsLabel: "🎯 Savings Goals",
    collectedLabel: "Collected",
    summaryTab: "Summary",
    transactionsTab: "Transactions",
    savingsTab: "Savings",
    advisorTab: "Advisor",
    monthlySummaryTitle: "This Month's Summary",
    thisMonthLabel: "This Month",
    incomeLabel: "Income",
    expenseLabel: "Expense",
    netBalanceLabel: "Net Balance",
    differenceLabel: "Difference",
    expenseByCategoryTitle: "Expense By Category",
    accountBalanceTitle: "Account Balance Distribution",
    noExpenseData: "No expense data yet",
    noAccountData: "No account data yet",
    categoryBreakdownTitle: "Category Breakdown",
    allCategories: "All",
    expenseOnly: "Expense",
    incomeOnly: "Income",
    percentageColumn: "Percentage",
    accountBalancesTitle: "Account Balances",
    byCategoryTitle: "By Category",
    categoryColumn: "Category",
    incomeColumn: "Income",
    expenseColumn: "Expense",
    byAccountTitle: "Balance By Account",
    accountColumn: "Account",
    balanceColumn: "Balance",
    addTransactionSubTab: "Add Transaction",
    fundTransferSubTab: "Fund Transfer",
    historySubTab: "Transaction History",
    addTransactionTitle: "Add Transaction",
    dateLabel: "Date",
    typeLabel: "Type",
    expenseOption: "Expense",
    incomeOption: "Income",
    categoryLabel: "Category",
    amountLabel: "Amount",
    descriptionLabel: "Description",
    saveTransactionButton: "Save Transaction",
    fundTransferTitle: "Fund Transfer",
    fromAccountLabel: "From Account",
    toAccountLabel: "To Account",
    selectSavingsGoalLabel: "Select Savings Goal",
    descriptionOptionalLabel: "Description (optional)",
    transferFundButton: "Transfer Fund",
    transactionHistoryTitle: "Transaction History",
    startDateLabel: "Start Date",
    endDateLabel: "End Date",
    searchDescriptionLabel: "Search Description",
    applyFilterButton: "Apply",
    resetFilterButton: "Reset",
    actionsColumn: "Actions",
    savingsGoalsTitle: "Savings Goals",
    savingsGoalInfo: "💡 Set your savings goals and track your progress monthly.",
    goalNameLabel: "Goal Name",
    targetAmountLabel: "Target Amount (Rp)",
    targetDateLabel: "Target Date",
    addGoalButton: "Add Goal",
    newChatButton: "New Chat",
    chatHistoryHeader: "Chat History",
    welcomeToAdvisor: "Welcome to Advisor AI",
    welcomeToAdvisorDesc: "Your SmartBudget Assistant. Start a conversation to get financial advice.",
    chatPlaceholder: "Type your message...",
    aiDisclaimer: "AI can make mistakes. Verify important information.",
    featureFinancialAnalysis: "Financial Analysis",
    featureSavingsAdvice: "Savings Advice",
    featureBudgetManagement: "Budget Management",
    typingIndicator: "AI is typing…",
    // Login page keys
    loginTitle: "Login",
    emailLabel: "Email/Username",
    passwordLabel: "Password",
    loginButton: "Login",
    dontHaveAccount: "Don't have an account?",
    registerLink: "Register here",
    // Register page keys
    registerTitle: "Register",
    registerSubtitle: "Create new account",
    fullNameLabel: "Full Name",
    registerButton: "Register",
    alreadyHaveAccount: "Already have an account?",
    loginLinkText: "Login here",
    registrationSuccess: "Registration successful! Redirecting to login...",
    emailAlreadyExists: "Email already registered",
    registrationFailed: "Registration failed",
    passwordWeak: "Weak",
    passwordFair: "Fair",
    passwordStrong: "Strong",
    passwordStrengthLabel: "Strength",
    agreeTermsLabel: "I agree to the <a href=\"/terms.html\" target=\"_blank\">Terms & Conditions</a> and <a href=\"/privacy.html\" target=\"_blank\">Privacy Policy</a>",
    agreeTermsPrefix: "I agree to the",
    termsLink: "Terms & Conditions",
    termsTitle: "Terms & Conditions",
    agreeTermsAnd: "and",
    privacyLink: "Privacy Policy",
    privacyTitle: "Privacy Policy",
    termsModalTitle: "Terms & Conditions",
    privacyModalTitle: "Privacy Policy",
    termsRequired: "You must agree to Terms & Conditions",
    // OTP Verification
    otpModalTitle: "Email Verification",
    otpSentMessage: "We've sent a verification code to your email",
    otpCodeLabel: "Verification Code (6 digits)",
    verifyButton: "Verify",
    resendOtpButton: "Resend",
    otpNotReceived: "Didn't receive the code?",
    otpVerifyingMessage: "Verifying code...",
    otpInvalidError: "Invalid OTP code",
    otpExpiredError: "OTP code has expired",
    generatePassword: "Generate Strong Password",
    generatePasswordHint: "Need a strong password?",
    passwordCopied: "Password copied to clipboard!",
    otpVerificationSuccess: "Verification successful! Your account has been created.",
    sendingOtp: "Sending verification code...",
    otpSentSuccess: "Verification code has been sent to your email",
    loginSuccess: "Login successful! Redirecting...",
    invalidEmail: "Invalid email or username",
    invalidPassword: "Invalid password",
    loginFailed: "Login failed",
    errorOccurred: "An error occurred",
    rememberMe: "Remember me",
    forgotPassword: "Forgot password?",
    recaptchaNoticeHtml: "This site is protected by reCAPTCHA and the Google <a href=\"https://policies.google.com/privacy\" target=\"_blank\" rel=\"noopener noreferrer\">Privacy Policy</a> and <a href=\"https://policies.google.com/terms\" target=\"_blank\" rel=\"noopener noreferrer\">Terms of Service</a> apply.",
    recaptchaNotice: "This site is protected by reCAPTCHA and the Google Privacy Policy and Terms of Service apply.",
    brandTagline: "Your Financial Companion",
    brandSubtitle: "Manage your finances smartly and structured.",
    featureTransactions: "Daily transaction recording",
    featureSavings: "Savings goals and progress",
    featureSummary: "Monthly summary and analysis",
    welcomeToSmartBudget: "Join SmartBudget",
    registerWelcomeMessage: "Start your financial journey with SmartBudget Assistant. Manage your finances easily and achieve your financial goals.",
    feature1: "Manage Finances Easily",
    feature2: "AI-Powered Financial Analysis",
    feature3: "Achieve Your Savings Goals",
    feature4: "Secure & Encrypted Data",
    // Forgot Password page
    forgotPasswordTitle: "Forgot Password",
    forgotPasswordDesc: "Enter your email. If registered, we will send a reset link.",
    sendResetLink: "Send Reset Link",
    backToLogin: "Back to Login",
    resetLinkSent: "If email is registered, reset link has been sent.",
    requestFailed: "Failed to process request",
    networkError: "Network error occurred",
    devModeNotice: "Test Mode:",
    smtpNotConfigured: "SMTP not configured. Use this link:",
    // Reset Password page
    resetPasswordTitle: "Reset Password",
    resetPasswordDesc: "Enter your new password.",
    newPasswordLabel: "New Password",
    confirmPasswordLabel: "Confirm Password",
    resetPasswordButton: "Reset Password",
    tokenNotFound: "Token not found. Please open reset link from email.",
    passwordMismatch: "Passwords do not match",
    passwordTooShort: "Password must be at least 6 characters",
    passwordResetSuccess: "Password successfully reset. Redirecting to login...",
    passwordResetFailed: "Failed to reset password",
    // Password reset API messages
    emailRequired: "Email is required",
    resetLinkSentIfRegistered: "If email is registered, reset link has been sent.",
    tokenAndPasswordRequired: "Token and new password are required",
    passwordMinLength: "Password must be at least 6 characters",
    invalidToken: "Invalid token",
    tokenExpired: "Token has expired",
    passwordResetSuccessLogin: "Password successfully reset. Please login.",
    passwordResetError: "Failed to reset password",
    // Profile page
    profileTitle: "Profile Information",
    profileName: "Name",
    profilePhone: "Phone Number",
    profileEmail: "Email",
    profileBio: "Short Bio",
    saveInfo: "Save Information",
    changePasswordTitle: "Change Password",
    currentPassword: "Current Password",
    newPassword: "New Password",
    confirmPassword: "Confirm New Password",
    savePassword: "Save Password",
    // Settings page
    settingsTitle: "Settings",
    settingsDesc: "Customize your preferences and application settings",
    languageTitle: "Language",
    languageDesc: "Choose the application interface language",
    themeTitle: "Theme",
    themeDesc: "Choose the application display theme",
    themeLight: "Light",
    themeDark: "Dark",
    themeAuto: "Auto",
    autoLogoutTitle: "Auto-Logout Timer",
    autoLogoutDesc: "Automatically log out after inactivity to enhance security",
    minutesLabel: "minutes",
    saveButton: "Save Settings",
    saveSuccess: "Settings saved successfully!",
    deleteAccountTitle: "Delete Account",
    deleteAccountDesc: "⚠️ This action cannot be undone. All your data will be permanently deleted.",
    deleteAccountBtn: "Delete My Account",
    confirmDeleteTitle: "Confirm Account Deletion",
    confirmDeleteWarning: "⚠️ You are about to permanently delete your account. All transactions, savings, and other data will be lost.",
    enterPasswordConfirm: "Enter your password to confirm:",
    understandDelete: "I understand that this action cannot be undone",
    cancelBtn: "Cancel",
    confirmDeleteBtn: "Delete Account",
    // Admin page
    userManagement: "User Management",
    addUser: "Add User",
    userId: "ID",
    userName: "Name",
    userEmail: "Email",
    userRole: "Role",
    actions: "Actions",
    addNewUser: "Add New User",
    cancel: "Cancel",
    save: "Save",
    resetPassword: "Reset Password",
    // User menu
    menuDashboard: "Dashboard",
    menuProfile: "Profile",
    menuSettings: "Settings",
    menuAdmin: "Admin Panel",
    menuLogout: "Logout",
  },
};

// Make translations available globally for login page
window.translations = translations;

// Category lists
const expenseCategories = [
  "Makan",
  "Jajan / Snack",
  "Belanja Stok",
  "Transport",
  "Laundry",
  "Tagihan",
  "Hiburan",
  "Belanja Umum",
  "Tunjangan Istri",
  "Kesehatan",
  "Lain-lain",
];

const incomeCategories = ["Gaji", "Lain-lain"];

function populateCategorySelect(selectEl, type, selected) {
  if (!selectEl) return;
  selectEl.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "-- Pilih Kategori --";
  selectEl.appendChild(placeholder);

  const list = type === "income" ? incomeCategories : expenseCategories;
  list.forEach((c) => {
    const opt = document.createElement("option");
    opt.value = c;
    opt.textContent = c;
    if (selected && selected === c) opt.selected = true;
    selectEl.appendChild(opt);
  });
}

function switchTab(tabName) {
  // Hide all tabs
  const tabs = document.querySelectorAll(".tab-content");
  tabs.forEach(tab => tab.classList.remove("active"));
  
  // Remove active class from all buttons
  const buttons = document.querySelectorAll(".tab-button");
  buttons.forEach(btn => btn.classList.remove("active"));
  
  // Show selected tab
  const selectedTab = document.getElementById(tabName);
  if (selectedTab) {
    selectedTab.classList.add("active");
  }
  
  // Mark clicked button as active
  if (event && event.target) {
    event.target.closest(".tab-button").classList.add("active");
  }
  
  // Auto-scroll chat to bottom when switching to advisor tab
  if (tabName === 'advisor') {
    ensureChatScrolledToBottom();
    
    // Re-populate model dropdown if it exists and is empty
    const modelSelect = document.getElementById('model-provider');
    if (modelSelect && window.chatProvider) {
      if (modelSelect.options.length === 0) {
        console.log('[ADVISOR] Re-populating dropdown on tab switch');
        window.populateModelSelect(window.chatProvider, window.chatModel, window.userRole || 'user');
      }
    }
  }
}

function switchSubTab(tabName) {
  // Hide all sub-tabs within the #transactions card
  const card = document.getElementById('transactions');
  const tabs = card.querySelectorAll(".sub-tab-content");
  tabs.forEach(tab => tab.classList.remove("active"));
  
  // Remove active class from all sub-tab buttons
  const buttons = card.querySelectorAll(".sub-tab-button");
  buttons.forEach(btn => btn.classList.remove("active"));
  
  // Show selected sub-tab and mark its button as active
  document.getElementById(tabName).classList.add("active");
  const activeButton = card.querySelector(`.sub-tab-button[onclick="switchSubTab('${tabName}')"]`);
  if (activeButton) activeButton.classList.add("active");
}

// Variabel untuk menyimpan data akun agar tidak perlu fetch berulang
let _accountData = { accounts: [], total_all: 0 };

// --- DATA LOADING FUNCTIONS ---

async function loadBalance() {
  const filter = document.getElementById('account-filter');
  const selectedAccount = filter ? filter.value : "";
  const balanceEl = document.getElementById("balance-amount");

  if (!balanceEl) return;

  if (selectedAccount) {
    // Jika akun spesifik dipilih, cari saldo dari data yang sudah ada
    const account = _accountData.accounts.find(a => a.account === selectedAccount);
    if (account) {
      balanceEl.textContent = formatCurrency(account.balance);
    } else {
      // Fallback jika tidak ditemukan (seharusnya tidak terjadi)
      balanceEl.textContent = formatCurrency(0);
    }
  } else {
    // Jika "Semua Akun" dipilih, gunakan total saldo dari _accountData
    balanceEl.textContent = formatCurrency(_accountData.total_all);
  }
}

async function loadSavings() {
  try {
    const res = await apiFetch("/api/savings");
    const data = await res.json();
    
    // Store globally for filtering
    window.allSavingsGoals = data;
    
    document.getElementById("savings-count").textContent = `${data.length} goals`;
    
    let totalSavings = 0;
    let totalProgress = 0;
    data.forEach(g => {
      totalSavings += g.current_amount;
      totalProgress += g.progress_pct;
    });
    document.getElementById("savings-total").textContent = `Terkumpul: ${formatCurrency(totalSavings)}`;
    
    // Update quick stats in active goals tab
    const totalGoalsEl = document.getElementById("total-goals-count");
    const totalSavedEl = document.getElementById("total-saved-amount");
    const avgProgressEl = document.getElementById("average-progress");
    
    if (totalGoalsEl) totalGoalsEl.textContent = data.length;
    if (totalSavedEl) totalSavedEl.textContent = formatCurrency(totalSavings);
    if (avgProgressEl) {
      const avgProg = data.length > 0 ? Math.round(totalProgress / data.length) : 0;
      avgProgressEl.textContent = `${avgProg}%`;
    }

    // Render goals using helper function
    if (typeof renderSavingsGoals === 'function') {
      renderSavingsGoals(data);
    } else {
      // Fallback to old rendering if helper not loaded
      const listDiv = document.getElementById("savings-list");
      if (listDiv) {
        listDiv.innerHTML = "";
        if (data.length === 0) {
          listDiv.innerHTML = `<div style="padding: 20px; text-align: center; color: #9ca3af;">
            <i class="fas fa-inbox" style="font-size: 32px; margin-bottom: 8px; display: block;"></i>
            Belum ada target tabungan. Mulai buat yang pertama!
          </div>`;
        } else {
          data.forEach((goal) => {
            const progressWidth = Math.min((goal.current_amount / goal.target_amount) * 100, 100);
            const card = document.createElement("div");
            card.style.cssText = "background: #f9fafb; border: 1.5px solid #e5e7eb; border-radius: 10px; padding: 14px; margin-bottom: 12px;";
            card.innerHTML = `
              <h3 style="margin: 0 0 4px 0; font-size: 16px; font-weight: 600; color: #1f2937;">${goal.name}</h3>
              <p style="margin: 0 0 10px 0; font-size: 12px; color: #6b7280;">${goal.description || ""}</p>
              <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px;">
                <span><strong>${formatCurrency(goal.current_amount)}</strong> / ${formatCurrency(goal.target_amount)}</span>
                <span style="font-weight: 600;">${goal.progress_pct}%</span>
              </div>
              <div style="background: #e5e7eb; border-radius: 999px; height: 8px; overflow: hidden;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); height: 100%; width: ${progressWidth}%;"></div>
              </div>
            `;
            listDiv.appendChild(card);
          });
        }
      }
    }

    // Populate savings goal selector in transfer form
    const goalSelector = document.getElementById('transfer-to-goal');
    if (goalSelector) {
      goalSelector.innerHTML = '<option value="">-- Pilih Target --</option>';
      data.forEach(goal => {
        const opt = document.createElement('option');
        opt.value = goal.id;
        opt.textContent = `${goal.name} (${formatCurrency(goal.current_amount)} / ${formatCurrency(goal.target_amount)})`;
        goalSelector.appendChild(opt);
      });
    }
  } catch (err) {
    console.error("Error loading savings:", err);
  }
}

function showError(element, message) {
  element.textContent = message;
  element.className = "small error";
  element.style.display = "block";
}

function showSuccess(element, message) {
  element.textContent = message;
  element.className = "small success";
  element.style.display = "block";
}

// Global chart instances
let expenseCategoryChart = null;
let accountBalanceChart = null;
let currentCategoryView = 'all';

function toggleCategoryView(view) {
  currentCategoryView = view;
  document.querySelectorAll('.toggle-btn').forEach(btn => btn.classList.remove('active'));
  event.target.classList.add('active');
  loadSummary(); // Reload to apply filter
}

// Make it globally accessible
window.toggleCategoryView = toggleCategoryView;

async function loadSummary() {
  try {
    const res = await apiFetch("/api/summary");
    const data = await res.json();
    
    // Update stat cards
    document.getElementById("sum-income").textContent = formatCurrency(data.total_income);
    document.getElementById("sum-expense").textContent = formatCurrency(data.total_expense);
    const netBalance = data.total_income - data.total_expense;
    document.getElementById("sum-net").textContent = formatCurrency(netBalance);
    
    // Update net balance color
    const netEl = document.getElementById("sum-net");
    if (netBalance > 0) {
      netEl.style.color = '#10b981';
    } else if (netBalance < 0) {
      netEl.style.color = '#ef4444';
    } else {
      netEl.style.color = '#6b7280';
    }
    
    // Render category table with filter
    const tbody = document.querySelector("#summary-table tbody");
    if (!tbody) return;
    tbody.innerHTML = '';
    
    const categories = data.categories || [];
    let filteredCategories = categories;
    
    if (currentCategoryView === 'expense') {
      filteredCategories = categories.filter(c => c.expense > 0);
    } else if (currentCategoryView === 'income') {
      filteredCategories = categories.filter(c => c.income > 0);
    }
    
    const totalAmount = currentCategoryView === 'expense' 
      ? data.total_expense 
      : currentCategoryView === 'income' 
        ? data.total_income 
        : data.total_expense + data.total_income;
    
    if (filteredCategories.length === 0) {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td colspan="4" style="text-align: center; color: #9ca3af; padding: 16px;">Belum ada data</td>`;
      tbody.appendChild(tr);
    } else {
      filteredCategories.forEach((c) => {
        const amount = currentCategoryView === 'expense' 
          ? c.expense 
          : currentCategoryView === 'income' 
            ? c.income 
            : c.expense + c.income;
        const percentage = totalAmount > 0 ? ((amount / totalAmount) * 100).toFixed(1) : 0;
        
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${c.category}</strong></td>
          <td style="text-align: right; color: #10b981;">${formatCurrency(c.income)}</td>
          <td style="text-align: right; color: #ef4444;">${formatCurrency(c.expense)}</td>
          <td style="text-align: right;">
            <span style="background: #eff6ff; color: #2563eb; padding: 4px 8px; border-radius: 6px; font-weight: 600; font-size: 11px;">
              ${percentage}%
            </span>
          </td>
        `;
        tbody.appendChild(tr);
      });
    }
    
    // Render expense category chart
    renderExpenseCategoryChart(categories);
    
  } catch (err) {
    console.error(err);
  }
}

function renderExpenseCategoryChart(categories) {
  const canvas = document.getElementById('expense-category-chart');
  const emptyState = document.getElementById('expense-chart-empty');
  
  if (!canvas) return;
  
  const expenseData = categories.filter(c => c.expense > 0);
  
  if (expenseData.length === 0) {
    canvas.style.display = 'none';
    emptyState.style.display = 'flex';
    return;
  }
  
  canvas.style.display = 'block';
  emptyState.style.display = 'none';
  
  // Destroy existing chart
  if (expenseCategoryChart) {
    expenseCategoryChart.destroy();
  }
  
  const labels = expenseData.map(c => c.category);
  const values = expenseData.map(c => c.expense);
  
  // Generate vibrant colors
  const colors = [
    '#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6',
    '#ec4899', '#14b8a6', '#f97316', '#06b6d4', '#6366f1'
  ];
  
  const ctx = canvas.getContext('2d');
  expenseCategoryChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: colors.slice(0, values.length),
        borderWidth: 2,
        borderColor: '#ffffff',
        hoverBorderWidth: 3,
        hoverBorderColor: '#ffffff',
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              const label = context.label || '';
              const value = formatCurrency(context.parsed);
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const percentage = ((context.parsed / total) * 100).toFixed(1);
              return `${label}: ${value} (${percentage}%)`;
            }
          },
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          padding: 12,
          bodyFont: {
            size: 13
          },
          titleFont: {
            size: 14,
            weight: 'bold'
          }
        }
      },
      cutout: '65%',
    }
  });
}

async function loadTransactions() {
  try {
    // respect account filter if set
    const params = new URLSearchParams();
    const accFilterEl = document.getElementById('account-filter');
    const acc = accFilterEl ? accFilterEl.value : "";
    if (acc) {
      params.append('account', acc);
    }

    // Add history filters
    const startDate = document.getElementById('filter-start-date').value;
    const endDate = document.getElementById('filter-end-date').value;
    const type = document.getElementById('filter-type').value;
    const query = document.getElementById('filter-q').value;

    if (startDate) params.append('start_date', startDate);
    if (endDate) params.append('end_date', endDate);
    if (type) params.append('type', type);
    if (query) params.append('q', query);

    let url = '/api/transactions';
    if (params.toString()) {
      url += `?${params.toString()}`;
    }
    const res = await apiFetch(url);
    const data = await res.json();
    const tbody = document.querySelector("#tx-table tbody");
    const emptyEl = document.getElementById('tx-empty');
    const paginationEl = document.getElementById('tx-pagination');
    if (!tbody) return;
    tbody.innerHTML = "";
    // Sort newest first by date (assuming YYYY-MM-DD)
    data.sort((a,b) => (b.date || '').localeCompare(a.date || ''));

    // Pagination logic: page size 10, show controls if > 10
    const pageSize = 10;
    const total = data.length;
    const totalPages = Math.ceil(total / pageSize);
    const state = loadTransactions._state || { page: 1 };
    if (state.page > totalPages) state.page = totalPages || 1;
    loadTransactions._state = state;

    const startIdx = (state.page - 1) * pageSize;
    const items = data.slice(startIdx, startIdx + pageSize);

    if (total === 0) {
      if (emptyEl) emptyEl.style.display = 'block';
      if (paginationEl) paginationEl.style.display = 'none';
    } else {
      if (emptyEl) emptyEl.style.display = 'none';
      items.forEach((tx) => {
        const tr = document.createElement("tr");
        let typeIcon, typeText, amountColor;
        if (tx.type === 'income') {
          typeIcon = '📈'; typeText = 'Pemasukan'; amountColor = '#10b981';
        } else if (tx.type === 'expense') {
          typeIcon = '📉'; typeText = 'Pengeluaran'; amountColor = '#ef4444';
        } else { // transfer
          typeIcon = '🔄'; typeText = 'Transfer'; amountColor = '#6b7280';
        }
        
        const amountDisplay = tx.type === 'transfer' ? tx.amount : Math.abs(tx.amount);

        tr.innerHTML = `
          <td>${tx.date}</td>
          <td>${typeIcon} ${typeText}</td>
          <td>${tx.category}</td>
          <td style="text-align: right; font-weight: 500; color: ${amountColor};">${formatCurrency(amountDisplay)}</td>
          <td>${tx.account || "—"}</td>
          <td class="actions">
            <button class="btn-edit" title="Edit" onclick="(async()=>{ const res = await apiFetch('/api/transactions'); const txs = await res.json(); const t = txs.find(x=>x.id===${tx.id}); if(t) openTransactionModal(t); })()"><i class='fas fa-pencil-alt'></i></button>
            <button class="btn-delete" title="Hapus" onclick="deleteTransaction(${tx.id})"><i class='fas fa-trash'></i></button>
          </td>
        `;
        tbody.appendChild(tr);
      });

      if (paginationEl) {
        if (totalPages > 1) {
          paginationEl.style.display = 'flex';
          paginationEl.innerHTML = '';
          for (let p = 1; p <= totalPages; p++) {
            const btn = document.createElement('button');
            btn.className = 'page-btn' + (p === state.page ? ' active' : '');
            btn.textContent = p;
            btn.addEventListener('click', () => {
              loadTransactions._state.page = p;
              loadTransactions();
            });
            paginationEl.appendChild(btn);
          }
        } else {
          paginationEl.style.display = 'none';
        }
      }
    }
  } catch (err) {
    console.error(err);
  }
}

async function loadAccounts() {
  try {
    const res = await apiFetch('/api/accounts');
    _accountData = await res.json(); // Simpan data ke variabel global
    const data = _accountData;
    // Exclude Blu savings account from balances display
    const visibleAccounts = (data.accounts || []).filter(a => a.account !== 'Blu Account (saving)');
    // Sort accounts by balance descending for display consistency
    const sortedAccounts = visibleAccounts.slice().sort((a, b) => (b.balance || 0) - (a.balance || 0));
    // Recalculate total_all to reflect only visible accounts (avoid mismatch with displayed grid)
    const totalVisible = sortedAccounts.reduce((sum, a) => sum + (a.balance || 0), 0);
    _accountData.total_all = totalVisible;
    
    const filter = document.getElementById('account-filter');
    if (filter) {
      // populate filter options (keep existing 'Semua Akun')
      // first remove all except first
      while (filter.options.length > 1) filter.remove(1);
    }

    // Populate filter
    sortedAccounts.forEach(a => {
      if (filter) {
        const opt = document.createElement('option');
        opt.value = a.account;
        opt.textContent = a.account;
        filter.appendChild(opt);
      }
    });

    // Render accounts grid
    const accountsGrid = document.getElementById('accounts-grid');
    if (accountsGrid) {
      accountsGrid.innerHTML = '';
      sortedAccounts.forEach(a => {
        const item = document.createElement('div');
        item.className = 'account-item';
        item.innerHTML = `
          <div class="account-name">
            <i class="fas fa-wallet"></i>
            ${a.account}
          </div>
          <div class="account-balance">${formatCurrency(a.balance)}</div>
        `;
        accountsGrid.appendChild(item);
      });
    }
    
    // Render account balance chart
    renderAccountBalanceChart(sortedAccounts);
    
  } catch (err) { console.error('Error loading accounts:', err); }
}

function renderAccountBalanceChart(accounts) {
  const canvas = document.getElementById('account-balance-chart');
  const emptyState = document.getElementById('account-chart-empty');
  
  if (!canvas) return;
  
  const accountsWithBalance = accounts.filter(a => a.balance > 0);
  
  if (accountsWithBalance.length === 0) {
    canvas.style.display = 'none';
    emptyState.style.display = 'flex';
    return;
  }
  
  canvas.style.display = 'block';
  emptyState.style.display = 'none';
  
  // Destroy existing chart
  if (accountBalanceChart) {
    accountBalanceChart.destroy();
  }
  
  const labels = accountsWithBalance.map(a => a.account);
  const values = accountsWithBalance.map(a => a.balance);
  
  // Generate colors
  const colors = [
    '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
    '#ec4899', '#14b8a6', '#f97316', '#06b6d4', '#6366f1'
  ];
  
  const ctx = canvas.getContext('2d');
  accountBalanceChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Saldo',
        data: values,
        backgroundColor: colors.slice(0, values.length).map(c => c + 'dd'),
        borderColor: colors.slice(0, values.length),
        borderWidth: 2,
        borderRadius: 8,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return formatCurrency(context.parsed.y);
            }
          },
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          padding: 12,
          bodyFont: {
            size: 13
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: function(value) {
              return 'Rp ' + (value / 1000000).toFixed(1) + 'M';
            },
            font: {
              size: 11
            }
          },
          grid: {
            color: '#f3f4f6'
          }
        },
        x: {
          ticks: {
            font: {
              size: 11
            }
          },
          grid: {
            display: false
          }
        }
      }
    }
  });
}

// --- CHAT FUNCTION ---

function appendChat(role, text, imageData = null, isLastUserMsg = false) {
  const box = document.getElementById("chat-box");
  if (!box) return;
  const div = document.createElement("div");
  
  if (role === "user") {
    div.className = "msg-user";
    let imageHtml = '';
    if (imageData) {
      imageHtml = `<div style="margin-bottom: 8px;"><img src="${imageData}" style="max-width: 300px; max-height: 300px; border-radius: 8px; border: 2px solid var(--border-color);" /></div>`;
    }
    const editBtn = isLastUserMsg ? `<button class="msg-user-edit-btn" title="Edit prompt"><i class="fas fa-pen"></i></button>` : '';
    const copyBtn = isLastUserMsg ? `<button class="msg-user-copy-btn" title="Copy prompt"><i class="fas fa-copy"></i></button>` : '';
    div.innerHTML = `
      <div class="msg-user-wrapper">
        <div class="msg-user-actions">
          ${copyBtn}
          ${editBtn}
        </div>
        <div class="msg-user-bubble">
          ${imageHtml}
          <div class="message-content">${escapeHtml(text)}</div>
        </div>
      </div>
      <div class="message-avatar">
        <i class="fas fa-user"></i>
      </div>
    `;
  } else {
    const messageId = 'msg-' + Date.now();
    div.className = "msg-bot";
    div.innerHTML = `
      <div class="message-avatar">
        <i class="fas fa-brain"></i>
      </div>
      <div class="message-body">
        <div class="message-content" id="${messageId}">${marked.parse(text)}</div>
        <div class="message-actions">
          <button class="message-action-btn" onclick="copyMessage('${messageId}')" title="Copy response">
            <i class="fas fa-copy"></i>
          </button>
          <button class="message-action-btn" onclick="regenerateResponse()" title="Redo">
            <i class="fas fa-redo"></i>
          </button>
        </div>
      </div>
    `;
  }
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function copyMessage(messageId) {
  const messageEl = document.getElementById(messageId);
  if (!messageEl) return;
  const text = messageEl.innerText;
  navigator.clipboard.writeText(text).then(() => {
    showTempNotification('Copied to clipboard!');
  }).catch(err => {
    console.error('Copy failed:', err);
  });
}

function getLastUserMessage() {
  const activeSession = getActiveSession();
  if (!activeSession || !activeSession.messages) return null;
  for (let i = activeSession.messages.length - 1; i >= 0; i--) {
    const m = activeSession.messages[i];
    if (m && m.role === 'user') return m;
  }
  return null;
}

function regenerateResponse() {
  const activeSession = chatData.sessions.find(s => s.id === chatData.activeSessionId);
  if (!activeSession || activeSession.messages.length < 2) return;
  
  // Remove last bot response
  activeSession.messages.pop();
  saveChatData();
  
  // Get last user message
  const lastUserMsg = activeSession.messages[activeSession.messages.length - 1];
  if (lastUserMsg && lastUserMsg.role === 'user') {
    document.getElementById('chat-input').value = lastUserMsg.content;
    document.getElementById('chat-form').requestSubmit();
  }
}

function showTempNotification(message) {
  const msgEl = document.getElementById('chat-msg');
  if (!msgEl) return;
  msgEl.textContent = message;
  msgEl.style.color = '#10b981';
  setTimeout(() => {
    msgEl.textContent = '';
    msgEl.style.color = '';
  }, 2000);
}

async function handleEditLastUserClick() {
  const lastUser = getLastUserMessage();
  if (!lastUser) {
    alert('Belum ada pesan user untuk diedit.');
    return;
  }
  const edited = prompt('Edit pesan terakhir:', lastUser.content || '');
  if (edited === null) return; // cancelled
  const trimmed = edited.trim();
  if (!trimmed) {
    alert('Pesan tidak boleh kosong.');
    return;
  }
  if (trimmed === lastUser.content) {
    showTempNotification('Tidak ada perubahan.');
    return;
  }

  const activeSession = getActiveSession();
  const sessionId = activeSession ? activeSession.sessionId : null;
  try {
    const updateRes = await apiFetch('/api/memory/logs/last-user', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: trimmed, session_id: sessionId, delete_following: true })
    });
    const updateData = await updateRes.json();
    if (!updateRes.ok) {
      throw new Error(updateData.error || 'Gagal menyimpan perubahan');
    }

    const modelSelectEl = document.getElementById('model-provider');
    const modelProvider = window.chatProvider || (localStorage.getItem('model_provider') || 'google');
    const modelId = modelSelectEl ? modelSelectEl.value : (localStorage.getItem('model') || null);
    const typingIndicator = document.getElementById("typing-indicator");
    const currentLang = localStorage.getItem('language') || 'id';
    const typingText = translations[currentLang].typingIndicator;
    typingIndicator.textContent = typingText;
    typingIndicator.style.display = 'flex';

    const regenerateRes = await apiFetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: trimmed,
        model_provider: modelProvider,
        model: modelId,
        lang: currentLang,
        session_id: sessionId || updateData.session_id,
        reuse_last_user: true
      })
    });
    const regenData = await regenerateRes.json();
    if (!regenerateRes.ok) {
      throw new Error(regenData.error || 'Gagal generate ulang');
    }

    typingIndicator.style.display = 'none';
    await loadChatData();
    showTempNotification('Pesan diedit dan di-generate ulang');
  } catch (err) {
    alert(err.message || 'Gagal edit/generate ulang');
  }
}

function setLanguage(lang) {
  if (!translations[lang]) lang = 'id'; // Default to ID
  localStorage.setItem('language', lang);

  // Update active button (support both .lang-button and .lang-btn classes)
  document.querySelectorAll('.lang-button, .lang-btn').forEach(btn => btn.classList.remove('active'));
  
  // Update header buttons (ID: lang-id, lang-en)
  const langBtn = document.getElementById(`lang-${lang}`);
  if (langBtn) langBtn.classList.add('active');
  
  // Update settings card buttons (ID: lang-id-card, lang-en-card)
  const langCardBtn = document.getElementById(`lang-${lang}-card`);
  if (langCardBtn) langCardBtn.classList.add('active');

  // Translate all elements with data-i18n attribute
  const t = translations[lang];
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (t[key]) {
      el.textContent = t[key];
    }
  });

  // Translate elements requiring HTML content (e.g., links)
  document.querySelectorAll('[data-i18n-html]').forEach(el => {
    const key = el.getAttribute('data-i18n-html');
    if (t[key]) {
      el.innerHTML = t[key];
    }
  });

  // Translate elements with data-i18n-placeholder
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    if (t[key]) {
      el.placeholder = t[key];
    }
  });

  // Translate elements with data-i18n-prefix
  document.querySelectorAll('[data-i18n-prefix]').forEach(el => {
    const key = el.getAttribute('data-i18n-prefix');
    const originalValue = el.textContent.split(': ')[1] || '';
    if (t[key]) {
      el.textContent = `${t[key]}: ${originalValue}`;
    }
  });

  // Reload data that might have language-specific content
  // For now, just savings total label might be affected
  if (document.getElementById("savings-total")) {
    const currentTotal = document.getElementById("savings-total").textContent.split(': ')[1] || 'Rp 0';
    document.getElementById("savings-total").textContent = `${t.collectedLabel}: ${currentTotal}`;
  }
  
  // Regenerate dynamic prompts with new language
  if (typeof generateDynamicPrompts === 'function') {
    generateDynamicPrompts();
  }
}

// Expose setLanguage globally for use in all pages
window.setLanguage = setLanguage;

/* --- CHAT SESSION MANAGEMENT (server truth, no localStorage cache) --- */
let chatData = { sessions: [], activeSessionId: null };

// Persist only in memory to avoid stale local copies when DB is cleared
function saveChatData() {
  /* no-op: source of truth is server */
}

async function loadChatData() {
  try {
    // Load only last 50 messages initially for faster load
    const res = await apiFetch('/api/memory/logs?limit=50&offset=0');
    const data = await res.json();
    const logs = (data && data.logs) ? data.logs : [];
    const sessionId = logs.length && logs[0].session_id ? logs[0].session_id : null;
    const sessionKey = sessionId ? `session-${sessionId}` : 'server-session';
    const messages = logs.slice().reverse().map(l => ({
      id: l.id,
      sessionId: l.session_id,
      role: l.role,
      content: l.content
    }));
    
    // Store total count for pagination
    const totalCount = data.total || 0;
    
    chatData.sessions = [
      {
        id: sessionKey,
        sessionId,
        title: 'Percakapan',
        messages,
        totalMessages: totalCount,
        loadedCount: logs.length
      }
    ];
    chatData.activeSessionId = sessionKey;
  } catch (err) {
    console.error('Failed to load chat logs from server:', err);
    chatData.sessions = [
      {
        id: 'server-session',
        sessionId: null,
        title: 'Percakapan',
        messages: [],
        totalMessages: 0,
        loadedCount: 0
      }
    ];
    chatData.activeSessionId = 'server-session';
  }

  renderChatSessions();
  loadActiveSession();
}

// Helper function to ensure chat is scrolled to bottom
function ensureChatScrolledToBottom() {
  const box = document.getElementById("chat-box");
  if (box && box.style.display !== 'none') {
    setTimeout(() => {
      box.scrollTop = box.scrollHeight;
    }, 50);
  }
}

// Load more messages when user scrolls to top
async function loadMoreMessages() {
  const activeSession = chatData.sessions.find(s => s.id === chatData.activeSessionId);
  if (!activeSession) return;
  
  const currentLoadedCount = activeSession.loadedCount || activeSession.messages.length;
  const totalMessages = activeSession.totalMessages || 0;
  
  // Only load if there are more messages
  if (currentLoadedCount >= totalMessages) return;
  
  try {
    const nextOffset = currentLoadedCount;
    const res = await apiFetch(`/api/memory/logs?limit=50&offset=${nextOffset}`);
    const data = await res.json();
    const logs = (data && data.logs) ? data.logs : [];
    
    // Reverse logs and add to beginning of messages array
    const newMessages = logs.slice().reverse().map(l => ({
      id: l.id,
      sessionId: l.session_id,
      role: l.role,
      content: l.content
    }));
    
    // Prepend new messages (maintain chronological order)
    activeSession.messages = [...newMessages, ...activeSession.messages];
    activeSession.loadedCount = currentLoadedCount + logs.length;
    
    // Refresh display without scrolling to bottom
    const box = document.getElementById("chat-box");
    const oldScrollHeight = box.scrollHeight;
    loadActiveSession();
    
    // Maintain scroll position (offset new height)
    const newScrollHeight = box.scrollHeight;
    box.scrollTop = newScrollHeight - oldScrollHeight;
  } catch (err) {
    console.error('Failed to load more messages:', err);
  }
}

function getActiveSession() {
  return chatData.sessions.find(s => s.id === chatData.activeSessionId);
}

function loadActiveSession() {
  const box = document.getElementById("chat-box");
  const welcomeScreen = document.getElementById("chat-welcome-screen");
  if (!box) return;
  
  box.innerHTML = '';
  
  // Ensure chatData.sessions is an array
  if (!chatData.sessions || !Array.isArray(chatData.sessions)) {
    chatData.sessions = [];
  }
  
  const activeSession = chatData.sessions.find(s => s.id === chatData.activeSessionId);
  
  if (activeSession && activeSession.messages && activeSession.messages.length > 0) {
    if (welcomeScreen) welcomeScreen.style.display = 'none';
    box.style.display = 'flex';
    
    // Find index of last user message
    let lastUserMsgIndex = -1;
    for (let i = activeSession.messages.length - 1; i >= 0; i--) {
      if (activeSession.messages[i].role === 'user') {
        lastUserMsgIndex = i;
        break;
      }
    }
    
    activeSession.messages.forEach((msg, idx) => {
      const isLastUserMsg = (msg.role === 'user' && idx === lastUserMsgIndex);
      appendChat(msg.role, msg.content, msg.image, isLastUserMsg);
    });
    
    // Attach event listener to last user message wrapper for edit button
    if (lastUserMsgIndex >= 0) {
      setTimeout(() => {
        const userMessages = box.querySelectorAll('.msg-user');
        if (userMessages.length > 0) {
          const lastUserMsg = userMessages[userMessages.length - 1];
          const editBtn = lastUserMsg.querySelector('.msg-user-edit-btn');
          const copyBtn = lastUserMsg.querySelector('.msg-user-copy-btn');
          if (editBtn) {
            editBtn.addEventListener('click', handleEditLastUserClick);
          }
          if (copyBtn) {
            copyBtn.addEventListener('click', () => {
              const msgContent = lastUserMsg.querySelector('.message-content');
              if (msgContent) {
                const text = msgContent.innerText;
                navigator.clipboard.writeText(text).then(() => {
                  showMessage('chat-msg', 'Prompt copied to clipboard!', 'success');
                }).catch(err => {
                  console.error('Failed to copy:', err);
                });
              }
            });
          }
        }
      }, 50);
    }
    
    // Auto-scroll to bottom
    setTimeout(() => {
      box.scrollTop = box.scrollHeight;
    }, 100);
  } else {
    // Show welcome screen if no active session or session is empty
    if (welcomeScreen) welcomeScreen.style.display = 'flex';
    box.style.display = 'none';
    generateDynamicPrompts(); // Generate new prompts for the welcome screen
  }
}

function renderChatSessions() {
  const listEl = document.getElementById('chat-session-list');
  if (!listEl) return;
  listEl.innerHTML = '';
  
  // Ensure chatData.sessions is an array
  if (!chatData.sessions || !Array.isArray(chatData.sessions)) {
    chatData.sessions = [];
  }
  
  chatData.sessions.forEach(session => {
    const item = document.createElement('div');
    item.className = 'session-item';
    item.dataset.id = session.id;
    item.innerHTML = `
      <i class="fas fa-comment-dots" style="color: #9ca3af;"></i>
      <span class="session-title">${session.title}</span>
      <div class="session-item-actions">
        <button class="rename-session-btn" title="Rename"><i class="fas fa-pencil-alt"></i></button>
        <button class="delete-session-btn" data-id="${session.id}" title="Delete"><i class="fas fa-trash-alt"></i></button>
      </div>
    `;
    if (session.id === chatData.activeSessionId) {
      item.classList.add('active');
    }
    
    const titleSpan = item.querySelector('.session-title');
    
    // Single click to open
    item.addEventListener('click', (e) => {
      if (e.target.closest('.session-item-actions')) return;
      chatData.activeSessionId = session.id;
      saveChatData();
      renderChatSessions();
      loadActiveSession();
    });

    // Rename button click
    const renameBtn = item.querySelector('.rename-session-btn');
    renameBtn.addEventListener('click', () => {
      const input = document.createElement('input');
      input.type = 'text';
      input.value = session.title;
      input.className = 'rename-input';
      
      item.querySelector('.session-item-actions').style.opacity = '0';
      titleSpan.replaceWith(input);
      input.focus();

      const saveRename = () => {
        const newTitle = input.value.trim();
        if (newTitle && newTitle !== session.title) {
          handleRenameSession(session.id, newTitle);
        } else {
          input.replaceWith(titleSpan);
          item.querySelector('.session-item-actions').style.opacity = '';
        }
      };

      input.addEventListener('blur', saveRename);
      input.addEventListener('keydown', (e) => { if (e.key === 'Enter') input.blur(); });
    });

    listEl.appendChild(item);
  });
}

async function createNewSession() {
  try {
    await apiFetch('/api/memory/clear', { method: 'DELETE' });
  } catch (err) {
    console.error('Failed to clear server chat logs:', err);
  }

  chatData.sessions = [
    {
      id: 'server-session',
      sessionId: null,
      title: `Obrolan ${new Date().toLocaleTimeString()}`,
      messages: []
    }
  ];
  chatData.activeSessionId = 'server-session';
  saveChatData();
  renderChatSessions();
  loadActiveSession();
}

function deleteSession(sessionId) {
  // Single server-backed session: deleting means clear and start fresh
  createNewSession();
}

function handleRenameSession(sessionId, newTitle) {
  const session = chatData.sessions.find(s => s.id === sessionId);
  if (session) session.title = newTitle;
  saveChatData();
  renderChatSessions();
}

function addMessageToActiveSession(role, content, imageData = null) {
  if (!chatData.activeSessionId) {
    createNewSession();
  }
  const activeSession = chatData.sessions.find(s => s.id === chatData.activeSessionId);
  if (activeSession) {
    // Ensure messages array exists
    if (!activeSession.messages) {
      activeSession.messages = [];
    }
    const message = { role, content, sessionId: activeSession.sessionId };
    if (imageData) {
      message.image = imageData;
    }
    activeSession.messages.push(message);
    // Auto-title the session based on the first user message
    if (activeSession.messages.length === 1 && role === 'user') {
      activeSession.title = content.substring(0, 25) + (content.length > 25 ? '...' : '');
    }
    saveChatData();
    renderChatSessions(); // Re-render to update title if changed
  }
}

async function generateDynamicPrompts() {
  const container = document.getElementById('dynamic-prompts-container');
  if (!container) return;
  container.innerHTML = ''; // Clear existing prompts

  let prompts = [];
  try {
    const summaryRes = await apiFetch("/api/summary");
    const summaryData = await summaryRes.json();
    if (summaryData.categories && summaryData.categories.length > 0) {
      const topCategory = summaryData.categories.reduce((prev, current) => (prev.expense > current.expense) ? prev : current);
      if (topCategory && topCategory.expense > 0) {
        const currentLang = localStorage.getItem('language') || 'id';
        const promptText = currentLang === 'id' 
          ? `Analisis pengeluaranku untuk kategori "${topCategory.category}".`
          : `Analyze my expenses for category "${topCategory.category}".`;
        prompts.push(promptText);
      }
    }
  } catch (err) {
    console.error("Failed to fetch data for dynamic prompts:", err);
  }

  const currentLang = localStorage.getItem('language') || 'id';
  const t = translations[currentLang];
  
  const genericPrompts = currentLang === 'id' ? [
    { icon: "fa-chart-line", text: "Ringkas pengeluaranku minggu lalu." },
    { icon: "fa-wallet", text: "Catat pengeluaran untuk kopi 25 ribu." },
    { icon: "fa-piggy-bank", text: "Buat target tabungan untuk dana darurat sebesar 5 juta." }
  ] : [
    { icon: "fa-chart-line", text: "Summarize my expenses last week." },
    { icon: "fa-wallet", text: "Record coffee expense for 25 thousand." },
    { icon: "fa-piggy-bank", text: "Create emergency fund savings target of 5 million." }
  ];
  
  const promptTexts = [...prompts, ...genericPrompts.map(p => p.text)];
  const finalPrompts = [...new Set(promptTexts)].slice(0, 4);

  finalPrompts.forEach((promptText, index) => {
    const promptObj = genericPrompts.find(p => p.text === promptText) || { icon: "fa-comment-dots", text: promptText };
    const card = document.createElement('div');
    card.className = 'prompt-card';
    card.innerHTML = `
      <i class="fas ${promptObj.icon}"></i>
      <span>${promptObj.text || promptText}</span>
    `;
    card.addEventListener('click', () => {
      document.getElementById('chat-input').value = promptObj.text || promptText;
      document.getElementById('chat-form').requestSubmit();
    });
    container.appendChild(card);
  });
}

// --- INITIALIZATION ---

async function init() {
  // Set default date = today
  const today = new Date().toISOString().slice(0, 10);
  document.getElementById("date").value = today;
  document.getElementById("goal-date").value = today;
  document.getElementById("transfer-date").value = today;

  // Language switcher
  const savedLang = localStorage.getItem('language') || 'id';
  setLanguage(savedLang);
  document.getElementById('lang-id').addEventListener('click', () => setLanguage('id'));
  document.getElementById('lang-en').addEventListener('click', () => setLanguage('en'));

  await loadAccounts(); // Muat akun dulu agar saldo total tersedia
  await loadBalance();
  await loadSavings();
  await loadSummary();
  await loadTransactions();

  // Populate category selects based on default types
  const mainType = document.getElementById("type");
  const mainCat = document.getElementById("category");
  if (mainType && mainCat) {
    populateCategorySelect(mainCat, mainType.value);
    mainType.addEventListener("change", (e) => populateCategorySelect(mainCat, e.target.value));
  }

  const editType = document.getElementById('edit-tx-type');
  const editCat = document.getElementById('edit-tx-category');
  if (editType && editCat) {
    editType.addEventListener('change', (e) => populateCategorySelect(editCat, e.target.value));
  }

  // Account filter event listener
  const accountFilter = document.getElementById('account-filter');
  if (accountFilter) {
    accountFilter.addEventListener('change', async () => {
      await loadBalance();
      await loadTransactions();
    });
  }

  // History filter buttons
  document.getElementById('btn-apply-filter').addEventListener('click', loadTransactions);
  document.getElementById('btn-reset-filter').addEventListener('click', () => {
    document.getElementById('history-filters').querySelectorAll('input, select').forEach(el => el.value = '');
    loadTransactions();
  });

  // Sidebar resizer
  const resizer = document.getElementById('sidebar-resizer');
  const sidebar = document.getElementById('chat-sidebar');
  let isResizing = false;

  resizer.addEventListener('mousedown', (e) => {
    e.preventDefault(); // Mencegah browser melakukan text selection saat drag
    isResizing = true;
    sidebar.classList.add('resizing'); // Tambahkan kelas untuk menonaktifkan transisi
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', () => {
      isResizing = false;
      sidebar.classList.remove('resizing'); // Hapus kelas setelah selesai
      document.removeEventListener('mousemove', handleMouseMove);
    });
  });

  function handleMouseMove(e) {
    if (isResizing) {
      // Hitung lebar baru berdasarkan posisi mouse relatif terhadap elemen induk
      const newWidth = e.clientX - sidebar.parentElement.getBoundingClientRect().left;
      sidebar.style.width = `${newWidth}px`;
    }
  }

  // Advisor sidebar functionality
  const collapseBtn = document.getElementById('collapse-sidebar-btn');
  const newChatCollapsedBtn = document.getElementById('new-chat-collapsed-btn');
  
  if (collapseBtn && sidebar) { // Gunakan variabel 'sidebar' yang sudah ada
    collapseBtn.addEventListener('click', () => {
      // Hapus style inline agar CSS class bisa mengambil alih
      sidebar.style.width = ''; 
      const isCurrentlyCollapsed = sidebar.classList.contains('collapsed');
      if (isCurrentlyCollapsed) {
        // Saat EXPAND: Kembalikan ke lebar terakhir yang disimpan, atau biarkan CSS yang mengatur
        const lastWidth = sidebar.getAttribute('data-last-width');
        sidebar.style.width = lastWidth ? `${lastWidth}px` : '';
      } else {
        // Saat COLLAPSE: Simpan lebar saat ini sebelum disembunyikan
        sidebar.setAttribute('data-last-width', sidebar.offsetWidth);
      }

      sidebar.classList.toggle('collapsed');
      const isCollapsed = sidebar.classList.contains('collapsed');
      collapseBtn.querySelector('i').className = isCollapsed ? 'fas fa-chevron-right' : 'fas fa-chevron-left';
      
      // Toggle new chat collapsed button visibility
      if (newChatCollapsedBtn) {
        newChatCollapsedBtn.style.display = isCollapsed ? 'flex' : 'none';
      }
    });
  }

  // New chat button (in sidebar)
  const newChatBtn = document.getElementById('new-chat-btn');
  if (newChatBtn) {
    newChatBtn.addEventListener('click', createNewSession);
  }

  // New chat button (when collapsed)
  if (newChatCollapsedBtn) {
    newChatCollapsedBtn.addEventListener('click', createNewSession);
  }

  // Delegated event listener for session deletion
  const sessionList = document.getElementById('chat-session-list');
  if (sessionList) {
    sessionList.addEventListener('click', (e) => {
      const deleteBtn = e.target.closest('.delete-session-btn');
      if (deleteBtn) {
        e.stopPropagation();
        if (confirm('Anda yakin ingin menghapus obrolan ini?')) {
          deleteSession(deleteBtn.dataset.id);
        }
      }
    });
  }
  loadChatData();
  
  // Add scroll listener for lazy loading more messages (throttled)
  const chatBox = document.getElementById('chat-box');
  if (chatBox) {
    const throttledLoadMore = throttle(() => {
      // Trigger load more when scrolled near top (100px)
      if (chatBox.scrollTop < 100) {
        loadMoreMessages();
      }
    }, 1000); // Throttle to max once per second
    
    chatBox.addEventListener('scroll', throttledLoadMore);
  }
  
  // Ensure chat is scrolled to bottom on initial page load
  setTimeout(() => {
    ensureChatScrolledToBottom();
  }, 300);
  // Form transaksi
  const txForm = document.getElementById("tx-form");
  const txMsg = document.getElementById("tx-msg");
  txForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    txMsg.textContent = "";

    const date = document.getElementById("date").value;
    const amount = parseAmount(document.getElementById("amount").value);
    const category = document.getElementById("category").value.trim();

    if (!date || amount <= 0 || !category) {
      showError(txMsg, "❌ Semua field (kecuali deskripsi) harus diisi.");
      return;
    }

    const payload = {
      date,
      type: document.getElementById("type").value,
      category,
      amount,
      account: document.getElementById("account").value.trim(),
      description: document.getElementById("description").value.trim(),
    };

    const btn = document.getElementById("btn-save");
    btn.disabled = true;

    try {
      const res = await apiFetch("/api/transactions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        showError(txMsg, `❌ ${data.error || "Gagal menyimpan"}`);
      } else {
        showSuccess(txMsg, "✅ Transaksi berhasil disimpan!");
        txForm.reset();
        document.getElementById("date").value = today;
        populateCategorySelect(mainCat, mainType.value);
        await loadSummary();
        await loadAccounts();
        await loadTransactions();
        await loadBalance();
      }
    } catch (err) {
      showError(txMsg, "❌ Error jaringan. Coba lagi.");
    } finally {
      btn.disabled = false;
    }
  });

  // Clear form button
  const btnClear = document.getElementById('btn-clear-tx');
  if (btnClear) {
    btnClear.addEventListener('click', () => {
      txForm.reset();
      document.getElementById("date").value = today;
      populateCategorySelect(mainCat, mainType.value);
      txMsg.textContent = '';
    });
  }

  // Form transfer dana
  const transferForm = document.getElementById("transfer-form");
  const transferMsg = document.getElementById("transfer-msg");
  const savingsGoalSelector = document.getElementById('savings-goal-selector');
  
  document.getElementById('transfer-to').addEventListener('change', (e) => {
    savingsGoalSelector.style.display = e.target.value === 'Blu Account (saving)' ? 'block' : 'none';
  });

  transferForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    transferMsg.textContent = "";

    const amount = parseAmount(document.getElementById("transfer-amount").value);
    const fromAccount = document.getElementById("transfer-from").value;
    const toAccount = document.getElementById("transfer-to").value;
    const goalId = document.getElementById('transfer-to-goal').value;

    if (amount <= 0 || !fromAccount || !toAccount) {
      showError(transferMsg, "❌ Jumlah, akun asal, dan akun tujuan harus diisi.");
      return;
    }
    if (toAccount === 'Blu Account (saving)' && !goalId) {
      showError(transferMsg, "❌ Pilih target tabungan tujuan.");
      return;
    }
    if (fromAccount === toAccount && toAccount !== 'Blu Account (saving)') {
      showError(transferMsg, "❌ Akun asal dan tujuan tidak boleh sama.");
      return;
    }

    const btn = document.getElementById("btn-transfer");
    btn.disabled = true;

    let apiUrl, payload;
    const commonPayload = {
      amount,
      from_account: fromAccount,
      date: document.getElementById("transfer-date").value,
      description: document.getElementById("transfer-desc").value.trim(),
    };

    if (toAccount === 'Blu Account (saving)') {
      apiUrl = '/api/transfer_to_savings';
      payload = { ...commonPayload, goal_id: parseInt(goalId) };
    } else {
      apiUrl = '/api/transfer';
      payload = { ...commonPayload, to_account: toAccount };
    }

    try {
      const res = await apiFetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        showError(transferMsg, `❌ ${data.error || "Gagal transfer"}`);
      } else {
        showSuccess(transferMsg, `✅ ${data.message || "Transfer berhasil!"}`);
        transferForm.reset();
        document.getElementById("transfer-date").value = today;
        await loadAllData();
      }
    } catch (err) {
      showError(transferMsg, "❌ Error jaringan.");
    } finally {
      btn.disabled = false;
    }
  });

  // Form savings goals
  const savingsForm = document.getElementById("savings-form");
  const goalMsg = document.getElementById("goal-msg");
  savingsForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    goalMsg.textContent = "";

    const name = document.getElementById("goal-name").value.trim();
    const target = parseAmount(document.getElementById("goal-target").value);

    if (!name || target <= 0) {
      showError(goalMsg, "❌ Nama dan target harus diisi.");
      return;
    }

    const payload = {
      name,
      target_amount: target,
      current_amount: 0,
      description: document.getElementById("goal-desc").value.trim(),
      target_date: document.getElementById("goal-date").value || null,
    };

    const btn = document.getElementById("btn-add-goal");
    btn.disabled = true;

    try {
      const res = await apiFetch("/api/savings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        showError(goalMsg, `❌ ${data.error || "Gagal membuat goal"}`);
      } else {
        showSuccess(goalMsg, "✅ Target berhasil ditambahkan!");
        savingsForm.reset();
        document.getElementById("goal-date").value = today;
        await loadSavings();
        await loadBalance();
      }
    } catch (err) {
      showError(goalMsg, "❌ Error jaringan.");
    } finally {
      btn.disabled = false;
    }
  });

  // Event delegation for deleting savings goals
  document.getElementById('savings-list').addEventListener('click', async (e) => {
    const deleteBtn = e.target.closest(".delete-goal-btn");
    if (deleteBtn) {
      const goalId = deleteBtn.dataset.id;
      if (!confirm("Hapus target ini?")) return;

      try {
        const res = await apiFetch("/api/savings", {
          method: "DELETE",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id: parseInt(goalId) }),
        });
        if (res.ok) {
          await loadSavings();
        } else {
          const data = await res.json();
          alert(`Gagal menghapus: ${data.error}`);
        }
      } catch (err) {
        alert("Error jaringan saat menghapus.");
      }
    }
  });

  // Form chat
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input");
  const chatMsg = document.getElementById("chat-msg");
  const btnChat = document.getElementById("btn-chat");
  const btnClearChat = document.getElementById("btn-clear-chat");

  // Auto-resize textarea
  if (chatInput) {
    chatInput.addEventListener('input', () => {
      chatInput.style.height = 'auto';
      chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
    });

    // Chat input: send on Enter, new line on Shift+Enter
    chatInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (!btnChat.disabled) {
          chatForm.requestSubmit();
        }
      }
    });
  }

  // Image upload handling
  const btnUploadImage = document.getElementById('btn-upload-image');
  const chatImageInput = document.getElementById('chat-image-input');
  const imagePreviewContainer = document.getElementById('image-preview-container');
  const chatImagePreview = document.getElementById('chat-image-preview');
  const removeImageBtn = document.getElementById('remove-image-btn');
  let selectedImageFile = null;
  let ocrEnabled = false;

  // Check OCR status and update button state
  async function checkOCRStatus() {
    try {
      const response = await apiFetch('/api/me');
      const userData = await response.json();
      ocrEnabled = userData.ocr_enabled || false;
      
      if (btnUploadImage) {
        if (ocrEnabled) {
          btnUploadImage.disabled = false;
          btnUploadImage.style.opacity = '1';
          btnUploadImage.style.cursor = 'pointer';
          const currentLang = localStorage.getItem('language') || 'id';
          btnUploadImage.title = currentLang === 'id' 
            ? 'Upload Gambar (Struk, Menu, Dokumen)' 
            : 'Upload Image (Receipts, Menus, Documents)';
        } else {
          btnUploadImage.disabled = true;
          btnUploadImage.style.opacity = '0.5';
          btnUploadImage.style.cursor = 'not-allowed';
          const currentLang = localStorage.getItem('language') || 'id';
          btnUploadImage.title = currentLang === 'id'
            ? '❌ Upload gambar tidak tersedia - Hubungi admin untuk mengaktifkan OCR'
            : '❌ Image upload not available - Contact admin to enable OCR';
        }
      }
    } catch (error) {
      console.error('Error checking OCR status:', error);
    }
  }

  // Check OCR status on page load
  checkOCRStatus();

  if (btnUploadImage && chatImageInput) {
    btnUploadImage.addEventListener('click', () => {
      if (!ocrEnabled) {
        const currentLang = localStorage.getItem('language') || 'id';
        const message = currentLang === 'id' 
          ? 'Fitur upload gambar belum diaktifkan. Silakan aktifkan OCR di menu Pengaturan terlebih dahulu.'
          : 'Image upload feature is not enabled. Please enable OCR in Settings first.';
        alert(message);
        return;
      }
      chatImageInput.click();
    });

    chatImageInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (!file) return;

      // Validate file type
      if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
        alert('Format file tidak didukung. Gunakan JPG, PNG, atau WebP.');
        chatImageInput.value = '';
        return;
      }

      // Validate file size (max 5MB)
      if (file.size > 5 * 1024 * 1024) {
        alert('Ukuran file terlalu besar. Maksimal 5MB.');
        chatImageInput.value = '';
        return;
      }

      // Show preview
      selectedImageFile = file;
      const reader = new FileReader();
      reader.onload = (event) => {
        chatImagePreview.src = event.target.result;
        imagePreviewContainer.style.display = 'block';
      };
      reader.readAsDataURL(file);
    });

    if (removeImageBtn) {
      removeImageBtn.addEventListener('click', () => {
        selectedImageFile = null;
        chatImageInput.value = '';
        imagePreviewContainer.style.display = 'none';
        chatImagePreview.src = '';
      });
    }
  }

  // Clear chat button
  if (btnClearChat) {
    btnClearChat.addEventListener('click', () => {
      if (confirm('Clear current chat? This will start a new conversation.')) {
        createNewSession();
      }
    });
  }

  if (chatForm) {
    chatForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const text = chatInput.value.trim();
      const hasImage = selectedImageFile !== null;
      if (!text && !hasImage) return;

      // Hide welcome screen and show chat box
      const welcomeScreen = document.getElementById("chat-welcome-screen");
      const chatBox = document.getElementById("chat-box");
      welcomeScreen.style.display = 'none';
      chatBox.style.display = 'flex';

      // Store image info if present
      let imageData = null;
      const imageFile = selectedImageFile; // Save reference before clearing
      if (imageFile) {
        const reader = new FileReader();
        imageData = await new Promise((resolve) => {
          reader.onload = (e) => resolve(e.target.result);
          reader.readAsDataURL(imageFile);
        });
      }

      addMessageToActiveSession('user', text, imageData);
      loadActiveSession(); // Reload to show the new user message and attach edit button

      chatInput.value = "";
      chatInput.style.height = 'auto';
      btnChat.disabled = true;
      
      // Clear image after sending
      selectedImageFile = null;
      chatImageInput.value = '';
      imagePreviewContainer.style.display = 'none';
      chatImagePreview.src = '';
      
      // Show typing indicator with translation
      const typingIndicator = document.getElementById("typing-indicator");
      const currentLang = localStorage.getItem('language') || 'id';
      const typingText = translations[currentLang].typingIndicator;
      typingIndicator.textContent = typingText;
      typingIndicator.style.display = 'flex';
      chatBox.scrollTop = chatBox.scrollHeight;

      const modelSelectEl = document.getElementById('model-provider');
      const modelProvider = window.chatProvider || (localStorage.getItem('model_provider') || 'google');
      const modelId = modelSelectEl ? modelSelectEl.value : (localStorage.getItem('model') || null);

      // --- Unified SSE Streaming for both providers ---
      // Declare streamDiv outside try-catch to be accessible in error handler
      let streamDiv = null;
      let streamContent = null;
      let streamActions = null;
      let streamMessageId = null;
      let fullResponseText = '';
      
      // Function to ensure stream container exists
      const ensureStreamContainer = () => {
        if (streamDiv) return;
        streamMessageId = `stream-${Date.now()}`;
        streamDiv = document.createElement("div");
        streamDiv.className = "msg-bot";
        streamDiv.innerHTML = `
          <div class="message-avatar"><i class="fas fa-brain"></i></div>
          <div class="message-body">
            <div class="message-content streaming-content" id="${streamMessageId}"></div>
            <div class="message-actions"></div>
          </div>
        `;
        chatBox.appendChild(streamDiv);
        streamContent = streamDiv.querySelector('.streaming-content');
        streamActions = streamDiv.querySelector('.message-actions');
      };
      
      try {
        let response;
        
        // Create abort controller for timeout (60 seconds)
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 60000);
        
        try {
          if (imageData) {
            // Use FormData for image upload
            const formData = new FormData();
            formData.append('message', text || 'Analyze this image');
            formData.append('image', imageFile);
            formData.append('model_provider', modelProvider);
            formData.append('model', modelId || '');
            formData.append('lang', localStorage.getItem('language') || 'id');
            console.log('[ADVISOR] Image upload - Provider:', modelProvider, 'Model:', modelId);
            
            response = await apiFetch('/api/chat', {
              method: 'POST',
              body: formData,
              signal: controller.signal
            });
          } else {
            // Regular JSON request
            console.log('[ADVISOR] Text chat - Provider:', modelProvider, 'Model:', modelId);
            response = await apiFetch('/api/chat', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ message: text, model_provider: modelProvider, model: modelId, lang: localStorage.getItem('language') || 'id' }),
              signal: controller.signal
            });
          }
        } finally {
          clearTimeout(timeoutId);
        }

        if (!response.ok) {
          // Try to extract JSON error
          let errMsg = `HTTP error! status: ${response.status}`;
          let errorCode = null;
          let suggestedModel = null;
          try {
            const data = await response.json();
            if (data && data.error) {
              errMsg = data.error;
              errorCode = data.error_code;
              suggestedModel = data.suggested_model;
            }
          } catch {}
          
          // Special handling for quota exceeded (429)
          if (errorCode === 'QUOTA_EXCEEDED' || response.status === 429) {
            typingIndicator.style.display = 'none';
            
            // Add error message to chat with suggestion
            const errorDiv = document.createElement("div");
            errorDiv.className = "msg-bot error-message";
            
            let errorMessage = escapeHtml(errMsg);
            if (suggestedModel) {
              errorMessage += `<br><br><button onclick="document.getElementById('model-provider').value='${suggestedModel}'; window.chatModel='${suggestedModel}'; localStorage.setItem('model', '${suggestedModel}'); showMessage('chat-msg', 'Model diganti ke ${suggestedModel}', 'success');" style="padding: 8px 16px; background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; margin-top: 8px;">🔄 Ganti ke ${suggestedModel}</button>`;
            }
            
            errorDiv.innerHTML = `
              <div class="message-avatar"><i class="fas fa-exclamation-circle"></i></div>
              <div class="message-body">
                <div class="message-content" style="color: #f59e0b;">
                  <strong>⏱️ Kuota API Habis</strong><br>
                  ${errorMessage}
                </div>
              </div>
            `;
            chatBox.appendChild(errorDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
            
            showMessage('chat-msg', 'Kuota model habis. Silakan pilih model lain.', 'warning');
            return;
          }
          
          // Special handling for premium restrictions
          if (errorCode === 'OPENAI_PREMIUM_ONLY' || errorCode === 'PREMIUM_MODEL_REQUIRED' || response.status === 403) {
            typingIndicator.style.display = 'none';
            
            // Add error message to chat
            const errorDiv = document.createElement("div");
            errorDiv.className = "msg-bot error-message";
            
            let errorMessage = escapeHtml(errMsg);
            if (errorCode === 'PREMIUM_MODEL_REQUIRED') {
              errorMessage += '<br><br><em>Model premium: GPT-5, GPT-5 Mini, GPT-5 Nano, dan Gemini 2.5 Pro memerlukan akun Premium.</em>';
            } else {
              errorMessage += '<br><br><em>Anda masih menggunakan provider OpenAI di settings. Silakan ganti ke Google Gemini atau upgrade ke Premium.</em>';
            }
            
            errorDiv.innerHTML = `
              <div class="message-avatar"><i class="fas fa-exclamation-triangle"></i></div>
              <div class="message-body">
                <div class="message-content" style="color: #dc3545;">
                  <strong>⚠️ Akses Terbatas</strong><br>
                  ${errorMessage}
                </div>
              </div>
            `;
            chatBox.appendChild(errorDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
            
            showMessage('chat-msg', errMsg, 'error');
            return;
          }
          
          throw new Error(errMsg);
        }

        const contentType = response.headers.get('Content-Type') || '';

        if (contentType.includes('text/event-stream')) {
          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          let buffer = '';

          const handleFrame = (frame) => {
            const lines = frame.split('\n').filter(Boolean);
            const eventLine = lines.find(l => l.startsWith('event:')) || '';
            const dataLine = lines.find(l => l.startsWith('data:')) || '';
            const eventName = eventLine ? eventLine.replace('event: ', '').trim() : '';
            const data = dataLine ? dataLine.replace('data: ', '') : '';
            if (eventName === 'error') {
              ensureStreamContainer();
              streamContent.innerHTML = `❌ ${escapeHtml(data)}`;
            } else if (dataLine) {
              ensureStreamContainer();
              fullResponseText += data;
              streamContent.innerHTML = marked.parse(fullResponseText);
              chatBox.scrollTop = chatBox.scrollHeight;
            }
          };

          while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const parts = buffer.split('\n\n');
            buffer = parts.pop();
            for (const frame of parts) handleFrame(frame);
          }
        } else {
          // Fallback: try JSON first, else treat as text
          let data = null;
          let isJson = false;
          try {
            const rawText = await response.text();
            // Simple heuristic to detect JSON
            isJson = rawText.trim().startsWith('{') || rawText.trim().startsWith('[');
            if (isJson) {
              data = JSON.parse(rawText);
            } else {
              // Treat as plain text answer from provider
              ensureStreamContainer();
              fullResponseText = rawText;
              streamContent.innerHTML = marked.parse(fullResponseText);
            }
          } catch (e) {
            // As a last resort, show a generic error
            ensureStreamContainer();
            streamContent.innerHTML = `❌ ${escapeHtml(e.message || 'Unexpected response')}`;
          }
          typingIndicator.style.display = 'none';
          if (isJson && data) {
            if (data.error) {
              ensureStreamContainer();
              streamContent.innerHTML = `❌ ${escapeHtml(data.error)}`;
            } else {
              const answer = (data.answer || data.content || data.text || '');
              ensureStreamContainer();
              fullResponseText = answer;
              streamContent.innerHTML = marked.parse(answer);
            }
          }
        }

        typingIndicator.style.display = 'none';
        if (fullResponseText) {
          addMessageToActiveSession('assistant', fullResponseText);
          // Add action buttons
          if (streamDiv && streamActions) {
            streamActions.innerHTML = `
              <button class="message-action-btn" onclick="copyMessage('${streamMessageId}')" title="Copy response">
                <i class="fas fa-copy"></i>
              </button>
              <button class="message-action-btn" onclick="regenerateResponse()" title="Redo">
                <i class="fas fa-redo"></i>
              </button>
            `;
          }
          // Check for success indicators and reload data
          if (fullResponseText.includes("✅") || fullResponseText.includes("berhasil")) {
            console.log("🔄 Success detected in LLM response, reloading all data...");
            await loadAllData();
            console.log("✅ Data reload complete");
          }
        }
      } catch (error) {
        typingIndicator.style.display = 'none';
        // Show error in the streaming container to avoid duplicate messages
        const box = document.getElementById("chat-box");
        if (!streamDiv) ensureStreamContainer();
        
        // Check for timeout
        if (error.name === 'AbortError') {
          const currentLang = localStorage.getItem('language') || 'id';
          const timeoutMsg = currentLang === 'id'
            ? '⏱️ Permintaan timeout (lebih dari 60 detik). Silakan coba lagi atau cek koneksi internet Anda.'
            : '⏱️ Request timeout (over 60 seconds). Please try again or check your internet connection.';
          streamContent.innerHTML = timeoutMsg;
        }
        // Check for OCR-specific error
        else if (error.message && error.message.includes('OCR_NOT_ENABLED')) {
          const currentLang = localStorage.getItem('language') || 'id';
          const errorMsg = currentLang === 'id'
            ? 'Fitur upload gambar belum diaktifkan. Silakan aktifkan OCR di <a href="/settings.html" style="color: #3b82f6; text-decoration: underline;">Pengaturan</a> terlebih dahulu.'
            : 'Image upload feature is not enabled. Please enable OCR in <a href="/settings.html" style="color: #3b82f6; text-decoration: underline;">Settings</a> first.';
          streamContent.innerHTML = `❌ ${errorMsg}`;
        } else {
          streamContent.innerHTML = `❌ ${escapeHtml(error.message || 'Terjadi error koneksi stream.')}`;
        }
        console.error('Streaming error:', error);
      } finally {
        btnChat.disabled = false;
      }
    });
  }
}

async function loadAllData() {
  await loadAccounts();
  await loadBalance();
  await loadSummary();
  await loadTransactions();
  await loadSavings();
}

// --- MODAL & ACTION FUNCTIONS ---

function openTransactionModal(tx) {
  if (!tx) return;
  document.getElementById('edit-tx-id').value = tx.id;
  document.getElementById('edit-tx-date').value = tx.date || '';
  document.getElementById('edit-tx-type').value = tx.type || 'expense';
  // populate edit category select according to type, and select the transaction category
  const editCat = document.getElementById('edit-tx-category');
  populateCategorySelect(editCat, tx.type || 'expense', tx.category);
  document.getElementById('edit-tx-amount').value = tx.amount || '';
  document.getElementById('edit-tx-account').value = tx.account || '';
  document.getElementById('edit-tx-description').value = tx.description || '';
  document.getElementById('transaction-edit-modal').classList.remove('hidden');
}

function closeTransactionModal() {
  document.getElementById('transaction-edit-modal').classList.add('hidden');
}

async function saveTransactionEdit(e) {
  e.preventDefault();
  const id = parseInt(document.getElementById('edit-tx-id').value);
  const payload = {
    date: document.getElementById('edit-tx-date').value,
    type: document.getElementById('edit-tx-type').value,
    category: document.getElementById('edit-tx-category').value,
    amount: parseAmount(document.getElementById('edit-tx-amount').value),
    account: document.getElementById('edit-tx-account').value,
    description: document.getElementById('edit-tx-description').value,
  };

  try {
    const res = await apiFetch(`/api/transactions/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      alert(data.error || 'Gagal update transaksi');
      return;
    }
    closeTransactionModal();
    await loadAllData();
  } catch (err) {
    console.error(err);
    alert('Error jaringan saat update transaksi');
  }
}

async function deleteTransaction(id) {
  if (!confirm('Hapus transaksi ini?')) return;
  try {
    const res = await apiFetch(`/api/transactions/${id}`, {
      method: 'DELETE',
    });
    const data = await res.json();
    if (!res.ok) {
      alert(data.error || 'Gagal menghapus transaksi');
      return;
    }
    await loadAllData();
  } catch (err) {
    console.error(err);
    alert('Error jaringan saat menghapus transaksi');
  }
}
function openSavingsEditModal(goal) {
  if (!goal) return;
  document.getElementById('edit-goal-id').value = goal.id;
  document.getElementById('edit-goal-name').value = goal.name;
  document.getElementById('edit-goal-target').value = goal.target_amount;
  document.getElementById('edit-goal-date').value = goal.target_date || '';
  document.getElementById('edit-goal-desc').value = goal.description || '';
  document.getElementById('savings-edit-modal').classList.remove('hidden');
}

function closeSavingsEditModal() {
  document.getElementById('savings-edit-modal').classList.add('hidden');
}

async function saveSavingsEdit(e) {
  e.preventDefault();
  const id = parseInt(document.getElementById('edit-goal-id').value);
  const name = document.getElementById('edit-goal-name').value;
  const targetAmount = parseAmount(document.getElementById('edit-goal-target').value);

  if (!name || targetAmount <= 0) {
    alert('Nama dan target amount harus diisi dengan benar.');
    return;
  }

  const payload = {
    id,
    name,
    target_amount: targetAmount,
    target_date: document.getElementById('edit-goal-date').value,
    description: document.getElementById('edit-goal-desc').value,
  };

  try {
    const res = await apiFetch(`/api/savings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const data = await res.json();
      alert(data.error || 'Gagal update target');
      return;
    }
    closeSavingsEditModal();
    await loadSavings();
  } catch (err) {
    alert('Error jaringan saat update target.');
  }
}
