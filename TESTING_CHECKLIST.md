# Testing Checklist - Financial Advisor

## ✅ Pre-Testing Setup

- [x] Backend server running on `http://localhost:8000` (Note: port 8000, not 5050)
- [x] Database initialized (users, transactions, savings tables)
- [x] `.env` file configured dengan DATABASE_URL dan API keys
- [ ] Browser cache cleared (Ctrl + Shift + R)

---

## 🔐 Authentication Tests

### Register & Login
- [ ] Register new user (username, email, password)
- [ ] Login dengan credentials yang benar
- [ ] Logout dan login kembali
- [ ] Error handling untuk wrong password
- [ ] Error handling untuk duplicate username

---

## 💬 Chat & AI Assistant Tests

### Basic Chat
- [ ] Create new chat session (klik "New Chat")
- [ ] Send message ke AI assistant
- [ ] AI responds dengan format markdown yang benar
- [ ] Chat history tersimpan di localStorage
- [ ] Switch between multiple sessions

### Chat Sessions
- [ ] Create multiple sessions
- [ ] Rename session (klik pencil icon)
- [ ] Delete session (klik trash icon)
- [ ] Active session highlighted
- [ ] Sessions persist setelah page reload

### AI Tool Calling (Financial Actions)

#### Add Transaction
Test dengan berbagai format:
- [ ] "Catat pengeluaran 50000 untuk makan"
- [ ] "Add expense Rp 25,000 for transport"
- [ ] "Record income 1 juta from salary"
- [ ] "Pengeluaran 15rb untuk kopi"
- [ ] Check transaction appears di transaction list

#### Transfer to Savings
- [ ] "Transfer 100000 ke tabungan vacation"
- [ ] "Pindahkan 50rb ke tabungan emergency"
- [ ] Check savings goal balance updated
- [ ] Check account balance reduced

#### Update Savings Goal
- [ ] "Update tabungan vacation, ubah deadline jadi 31 Desember 2025"
- [ ] "Ubah target tabungan emergency jadi 5 juta"
- [ ] Check changes reflected di savings list

#### View Summary
- [ ] "Berapa total pengeluaran bulan ini?"
- [ ] "Tampilkan ringkasan keuangan"
- [ ] "Show my balance"

---

## 💰 Transaction Management Tests

### Add Transaction (Manual via Tab)
- [ ] Switch ke "Transaksi" tab
- [ ] Add income transaction
  - Amount, category, date, account, description
- [ ] Add expense transaction
  - Different account (BCA, BRI, Gopay, dll)
- [ ] Transaction appears in list immediately
- [ ] Balance updated correctly

### Transaction List
- [ ] View all transactions
- [ ] Edit transaction
- [ ] Delete transaction
- [ ] Balance recalculated after delete
- [ ] Filter by date/category (if implemented)

---

## 🎯 Savings Goal Tests

### Create Savings Goal
- [ ] Klik "Buat Goal Baru" di tab Tabungan
- [ ] Enter: goal name, target amount, deadline
- [ ] Goal appears in list
- [ ] Progress bar shows 0%

### Update Progress
- [ ] Add transaction with savings goal reference
- [ ] Or use AI: "Transfer 100rb ke tabungan vacation"
- [ ] Progress bar updates
- [ ] Percentage calculated correctly

### Edit Goal
- [ ] Click edit icon on savings goal
- [ ] Change target amount
- [ ] Change deadline
- [ ] Changes saved

### Delete Goal
- [ ] Delete savings goal
- [ ] Confirm removed from list

---

## 📊 Summary & Dashboard Tests

### Monthly Summary
- [ ] View ringkasan bulan ini di tab "Ringkasan"
- [ ] Income total correct
- [ ] Expense total correct
- [ ] Net balance calculated (income - expense)
- [ ] Category breakdown chart displays
- [ ] Account distribution chart displays

### Balance Display
- [ ] Total balance shown di header
- [ ] Filter by account (dropdown)
- [ ] Balance updates after transactions
- [ ] Correct for each account type

---

## 👤 Profile & Settings Tests

### Profile Page
- [ ] View user profile
- [ ] Upload avatar image
- [ ] Edit profile information
- [ ] Changes saved and displayed

### Settings Page
- [ ] Change password
- [ ] Update preferences (if any)
- [ ] Save settings

---

## 🔧 Performance & UX Tests

### Speed
- [ ] Chat response time < 3 seconds
- [ ] Transaction add < 1 second
- [ ] Page load < 2 seconds
- [ ] No lag when typing in chat

### No Errors
- [ ] No console errors in browser (F12)
- [ ] No 500 errors from backend
- [ ] No undefined/null errors
- [ ] No sync errors (removed)

### Responsive
- [ ] Works di mobile screen size
- [ ] Works di tablet screen size
- [ ] Works di desktop screen size

---

## 🌐 Language & Timezone Tests

### Language Support
- [ ] Switch language ID ↔ EN
- [ ] UI text changes
- [ ] Chat works in both languages
- [ ] AI understands Indonesian
- [ ] AI understands English

### Timezone (WIB)
- [ ] Transactions show correct WIB time
- [ ] Chat timestamps in WIB
- [ ] Default date is today (WIB)
- [ ] "Hari ini" / "Today" works correctly

---

## 🐛 Edge Cases & Error Handling

### Invalid Input
- [ ] Empty chat message (should not send)
- [ ] Invalid transaction amount (negative, text)
- [ ] Invalid date format
- [ ] Missing required fields

### Network Errors
- [ ] Backend offline → graceful error message
- [ ] API key invalid → error handling
- [ ] Timeout → retry mechanism

### Data Issues
- [ ] Empty transaction list displays message
- [ ] Empty savings goal list displays message
- [ ] No chat sessions → welcome screen shows
- [ ] Account not found → error message

---

## 🔄 Session & Data Persistence

### LocalStorage
- [ ] Chat data persists after reload
- [ ] Active session persists
- [ ] Auth token persists
- [ ] Clear localStorage → redirects to login

### Database
- [ ] Transactions saved to database
- [ ] Savings goals saved to database
- [ ] Chat logs saved to database (llm_logs)
- [ ] User data persists across sessions

---

## 📱 Multi-Session Tests

### Multiple Browser Tabs
- [ ] Open 2+ tabs same user
- [ ] Add transaction in tab 1
- [ ] Refresh tab 2 → sees new transaction
- [ ] Chat in both tabs independently

### Multiple Users
- [ ] User 1 and User 2 logged in separately
- [ ] User 1 data not visible to User 2
- [ ] Transactions isolated per user
- [ ] Chat sessions isolated per user

---

## 🎨 UI/UX Quality Tests

### Visual Polish
- [ ] Icons displayed correctly
- [ ] Colors consistent
- [ ] Fonts readable
- [ ] Spacing appropriate
- [ ] No layout breaks

### Animations
- [ ] Smooth transitions
- [ ] Loading indicators show when needed
- [ ] No jarring UI changes

### Accessibility
- [ ] Tab navigation works
- [ ] Focus states visible
- [ ] Error messages clear

---

## 📝 Final Checklist

Before considering testing complete:
- [ ] All critical features work
- [ ] No console errors
- [ ] No backend errors
- [ ] Performance acceptable
- [ ] User experience smooth
- [ ] Data persists correctly
- [ ] Ready for production

---

## 🚨 Known Issues to Watch For

- ~~Session sync causing lag~~ ✅ FIXED (removed sync)
- ~~Cannot read properties of undefined (messages)~~ ✅ FIXED
- ~~PostgreSQL changes() function error~~ ✅ FIXED (use rowcount)
- ~~DELETE CASCADE not working~~ ✅ FIXED (constraints updated)

---

## 📊 Test Results

**Date**: _____________________

**Tester**: _____________________

**Pass Rate**: _____ / _____ tests passed

**Critical Issues Found**:
1. 
2. 
3. 

**Notes**:
