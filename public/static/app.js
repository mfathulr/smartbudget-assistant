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

  const response = await fetch(url, { ...options, headers });

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

  // Add active page badge next to title
  const titleEl = document.querySelector('header h1');
  if (titleEl) {
    const path = window.location.pathname;
    let page = 'Dashboard';
    if (path.includes('admin')) page = 'Admin';
    else if (path.includes('profile')) page = 'Profile';
    else if (path.includes('settings')) page = 'Settings';
    else if (path.includes('login')) page = 'Login';
    const badge = document.createElement('span');
    badge.className = 'page-badge';
    badge.textContent = page;
    titleEl.appendChild(badge);
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
    welcomeToAdvisorDesc: "Asisten keuangan pintar Anda. Mulai percakapan untuk mendapatkan saran finansial.",
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
    loginSuccess: "Login berhasil! Mengalihkan...",
    invalidEmail: "Email atau username tidak valid",
    invalidPassword: "Password tidak valid",
    loginFailed: "Login gagal",
    errorOccurred: "Terjadi kesalahan",
    brandSubtitle: "Kelola keuangan dengan cerdas dan terstruktur.",
    featureTransactions: "Pencatatan transaksi harian",
    featureSavings: "Target tabungan dan progress",
    featureSummary: "Ringkasan dan analisis bulanan",
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
    languageTitle: "Bahasa",
    languageDesc: "Pilih bahasa antarmuka aplikasi.",
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
    welcomeToAdvisorDesc: "Your smart financial assistant. Start a conversation to get financial advice.",
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
    loginSuccess: "Login successful! Redirecting...",
    invalidEmail: "Invalid email or username",
    invalidPassword: "Invalid password",
    loginFailed: "Login failed",
    errorOccurred: "An error occurred",
    brandSubtitle: "Manage your finances smartly and structured.",
    featureTransactions: "Daily transaction recording",
    featureSavings: "Savings goals and progress",
    featureSummary: "Monthly summary and analysis",
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
    languageTitle: "Language",
    languageDesc: "Choose the application interface language.",
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

function appendChat(role, text) {
  const box = document.getElementById("chat-box");
  if (!box) return;
  const div = document.createElement("div");
  
  if (role === "user") {
    div.className = "msg-user";
    div.innerHTML = `
      <div class="message-content">${escapeHtml(text)}</div>
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
      <div>
        <div class="message-content" id="${messageId}">${marked.parse(text)}</div>
        <div class="message-actions">
          <button class="message-action-btn" onclick="copyMessage('${messageId}')" title="Copy">
            <i class="fas fa-copy"></i> Copy
          </button>
          <button class="message-action-btn" onclick="regenerateResponse()" title="Regenerate">
            <i class="fas fa-redo"></i> Regenerate
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

function setLanguage(lang) {
  if (!translations[lang]) lang = 'id'; // Default to ID
  localStorage.setItem('language', lang);

  // Update active button
  document.querySelectorAll('.lang-button').forEach(btn => btn.classList.remove('active'));
  document.getElementById(`lang-${lang}`).classList.add('active');

  // Translate all elements with data-i18n attribute
  const t = translations[lang];
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (t[key]) {
      el.textContent = t[key];
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

/* --- CHAT SESSION MANAGEMENT --- */
let chatData = { sessions: [], activeSessionId: null };

function generateUUID() {
  return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
    (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
  );
}

function saveChatData() {
  localStorage.setItem('chatData', JSON.stringify(chatData));
}

function loadChatData() {
  const data = localStorage.getItem('chatData');
  if (data) {
    chatData = JSON.parse(data);
    // Ensure all sessions have messages array
    if (chatData.sessions) {
      chatData.sessions.forEach(s => {
        if (!s.messages) s.messages = [];
      });
    }
    if (!chatData.activeSessionId && chatData.sessions.length > 0) {
      chatData.activeSessionId = chatData.sessions[0].id;
    }
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
    activeSession.messages.forEach(msg => {
      appendChat(msg.role, msg.content); // Render message without saving again
    });
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

function createNewSession() {
  const newId = generateUUID();
  const newSession = {
    id: newId,
    title: `Obrolan ${new Date().toLocaleTimeString()}`,
    messages: []
  };
  chatData.sessions.unshift(newSession);
  chatData.activeSessionId = newId;
  saveChatData();
  renderChatSessions();
  loadActiveSession();
}

function deleteSession(sessionId) {
  chatData.sessions = chatData.sessions.filter(s => s.id !== sessionId);
  if (chatData.activeSessionId === sessionId) {
    chatData.activeSessionId = chatData.sessions.length > 0 ? chatData.sessions[0].id : null;
  }
  saveChatData();
  renderChatSessions();
  loadActiveSession();
}

function handleRenameSession(sessionId, newTitle) {
  const session = chatData.sessions.find(s => s.id === sessionId);
  if (session) session.title = newTitle;
  saveChatData();
  renderChatSessions();
}

function addMessageToActiveSession(role, content) {
  if (!chatData.activeSessionId) {
    createNewSession();
  }
  const activeSession = chatData.sessions.find(s => s.id === chatData.activeSessionId);
  if (activeSession) {
    // Ensure messages array exists
    if (!activeSession.messages) {
      activeSession.messages = [];
    }
    activeSession.messages.push({ role, content });
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
      if (!text) return;

      // Hide welcome screen and show chat box
      const welcomeScreen = document.getElementById("chat-welcome-screen");
      const chatBox = document.getElementById("chat-box");
      welcomeScreen.style.display = 'none';
      chatBox.style.display = 'flex';

      addMessageToActiveSession('user', text);
      loadActiveSession(); // Reload to show the new user message

      chatInput.value = "";
      chatInput.style.height = 'auto';
      btnChat.disabled = true;
      
      // Show typing indicator with translation
      const typingIndicator = document.getElementById("typing-indicator");
      const currentLang = localStorage.getItem('language') || 'id';
      const typingText = translations[currentLang].typingIndicator;
      typingIndicator.textContent = typingText;
      typingIndicator.style.display = 'flex';
      chatBox.scrollTop = chatBox.scrollHeight;

      const modelProvider = document.getElementById('model-provider').value;

      // --- Logika Berbeda Berdasarkan Provider ---

      // --- Unified SSE Streaming for both providers ---
      try {
        const response = await apiFetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: text, model_provider: modelProvider, lang: localStorage.getItem('language') || 'id' })
        });
        if (!response.ok) {
          // Try to extract JSON error
          let errMsg = `HTTP error! status: ${response.status}`;
          try {
            const data = await response.json();
            if (data && data.error) errMsg = data.error;
          } catch {}
          throw new Error(errMsg);
        }

        const contentType = response.headers.get('Content-Type') || '';
        let fullResponseText = '';
        let streamDiv = null;
        let streamContent = null;
        const ensureStreamContainer = () => {
          if (streamDiv) return;
          streamDiv = document.createElement("div");
          streamDiv.className = "msg-bot";
          streamDiv.innerHTML = `
            <div class="message-avatar"><i class="fas fa-brain"></i></div>
            <div><div class="message-content streaming-content"></div></div>
          `;
          chatBox.appendChild(streamDiv);
          streamContent = streamDiv.querySelector('.streaming-content');
        };

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
            const rawText = await response.clone().text();
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
              const answer = (data.answer || data.content || data.text || '')
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
          if (streamDiv) {
            streamDiv.querySelector('div > div').insertAdjacentHTML('beforeend', `
            <div class="message-actions">
              <button class="message-action-btn" onclick="copyMessage('stream-${Date.now()}')" title="Copy">
                <i class="fas fa-copy"></i> Copy
              </button>
              <button class="message-action-btn" onclick="regenerateResponse()" title="Regenerate">
                <i class="fas fa-redo"></i> Regenerate
              </button>
            </div>
          `);
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
        streamContent.innerHTML = `❌ ${escapeHtml(error.message || 'Terjadi error koneksi stream.')}`;
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
