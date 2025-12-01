// Savings tab helper functions

function switchSavingsSubTab(tabName) {
  // Hide all sub-tab contents
  document.querySelectorAll('#savings .sub-tab-content').forEach(el => {
    el.classList.remove('active');
  });
  
  // Remove active class from all sub-tab buttons
  document.querySelectorAll('#savings .sub-tab-button').forEach(btn => {
    btn.classList.remove('active');
  });
  
  // Show selected sub-tab content
  const targetTab = document.getElementById(tabName);
  if (targetTab) {
    targetTab.classList.add('active');
  }
  
  // Add active class to clicked button
  event.target.classList.add('active');
}

function applySavingsFilter() {
  const sortValue = document.getElementById('sort-goals')?.value;
  const searchValue = document.getElementById('search-goals')?.value.toLowerCase() || '';
  
  if (!window.allSavingsGoals) return;
  
  let filtered = [...window.allSavingsGoals];
  
  // Filter by search
  if (searchValue) {
    filtered = filtered.filter(g => 
      g.name.toLowerCase().includes(searchValue) || 
      (g.description && g.description.toLowerCase().includes(searchValue))
    );
  }
  
  // Sort
  if (sortValue) {
    filtered.sort((a, b) => {
      switch(sortValue) {
        case 'progress-asc': return a.progress_pct - b.progress_pct;
        case 'progress-desc': return b.progress_pct - a.progress_pct;
        case 'deadline-asc': 
          if (!a.target_date) return 1;
          if (!b.target_date) return -1;
          return new Date(a.target_date) - new Date(b.target_date);
        case 'amount-desc': return b.target_amount - a.target_amount;
        case 'name-asc': return a.name.localeCompare(b.name);
        default: return 0;
      }
    });
  }
  
  renderSavingsGoals(filtered);
}

function renderSavingsGoals(data) {
  const listDiv = document.getElementById("savings-list");
  const completedListDiv = document.getElementById("completed-savings-list");
  
  if (!listDiv) return;
  
  listDiv.innerHTML = "";
  if (completedListDiv) completedListDiv.innerHTML = "";
  
  const activeGoals = data.filter(g => g.progress_pct < 100);
  const completedGoals = data.filter(g => g.progress_pct >= 100);
  
  // Render active goals
  if (activeGoals.length === 0) {
    listDiv.innerHTML = `<div style="padding: 40px 20px; text-align: center; color: #9ca3af; background: #f9fafb; border-radius: 8px; border: 1.5px dashed #e5e7eb;">
      <i class="fas fa-bullseye" style="font-size: 48px; margin-bottom: 12px; display: block; opacity: 0.5;"></i>
      <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Belum ada target tabungan</p>
      <p style="font-size: 14px; margin: 0;">Klik "Tambah Target" untuk membuat target tabungan pertama Anda!</p>
    </div>`;
  } else {
    activeGoals.forEach((goal) => {
      listDiv.appendChild(createGoalCard(goal));
    });
  }
  
  // Render completed goals
  if (completedListDiv) {
    if (completedGoals.length === 0) {
      completedListDiv.innerHTML = `<div style="padding: 40px 20px; text-align: center; color: #9ca3af; background: #f9fafb; border-radius: 8px; border: 1.5px dashed #e5e7eb;">
        <i class="fas fa-trophy" style="font-size: 48px; margin-bottom: 12px; display: block; opacity: 0.5;"></i>
        <p style="font-size: 16px; font-weight: 600; margin-bottom: 8px;">Belum ada target yang tercapai</p>
        <p style="font-size: 14px; margin: 0;">Terus menabung untuk mencapai target Anda!</p>
      </div>`;
    } else {
      completedGoals.forEach((goal) => {
        completedListDiv.appendChild(createGoalCard(goal, true));
      });
    }
  }
}

function createGoalCard(goal, isCompleted = false) {
  const progressWidth = Math.min((goal.current_amount / goal.target_amount) * 100, 100);
  const daysLeft = goal.target_date 
    ? Math.ceil((new Date(goal.target_date) - new Date()) / (1000 * 60 * 60 * 24))
    : null;
  const daysText = daysLeft !== null 
    ? (daysLeft > 0 ? `${daysLeft} hari lagi` : (daysLeft === 0 ? "Hari ini!" : `${Math.abs(daysLeft)} hari lalu`))
    : "Tidak ada deadline";

  const card = document.createElement("div");
  card.style.cssText = `
    background: ${isCompleted ? 'linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%)' : '#ffffff'}; 
    border: 1.5px solid ${isCompleted ? '#10b981' : '#e5e7eb'}; 
    border-radius: 12px; 
    padding: 16px; 
    margin-bottom: 12px;
    transition: all 0.3s ease;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
  `;
  card.onmouseenter = () => card.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
  card.onmouseleave = () => card.style.boxShadow = '0 1px 3px rgba(0,0,0,0.05)';
  
  const remaining = goal.target_amount - goal.current_amount;
  const monthlyNeeded = daysLeft && daysLeft > 0 ? Math.ceil(remaining / (daysLeft / 30)) : 0;
  
  card.innerHTML = `
    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 12px;">
      <div style="flex: 1;">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
          <h3 style="margin: 0; font-size: 17px; font-weight: 700; color: ${isCompleted ? '#047857' : '#1f2937'};">${goal.name}</h3>
          ${isCompleted ? '<span style="background: #10b981; color: white; font-size: 10px; padding: 2px 8px; border-radius: 12px; font-weight: 600;"><i class="fas fa-check"></i> TERCAPAI</span>' : ''}
        </div>
        <p style="margin: 0; font-size: 13px; color: #6b7280;">${goal.description || "Tanpa deskripsi"}</p>
      </div>
      <div style="display: flex; gap: 6px;">
        <button onclick='openSavingsEditModal(${JSON.stringify(goal).replace(/'/g, "&apos;")})' class="btn-edit" style="padding: 7px 12px; font-size: 12px;" title="Edit target">
          <i class="fas fa-pencil-alt"></i>
        </button>
        <button class="delete-goal-btn btn-delete" data-id="${goal.id}" style="padding: 7px 12px; font-size: 12px;" title="Hapus target">
          <i class="fas fa-trash"></i>
        </button>
      </div>
    </div>
    
    <div style="margin-bottom: 12px;">
      <div style="display: flex; justify-content: space-between; font-size: 14px; margin-bottom: 8px;">
        <span style="color: #374151;"><strong>${window.formatCurrency(goal.current_amount)}</strong> dari ${window.formatCurrency(goal.target_amount)}</span>
        <span style="color: ${isCompleted ? '#10b981' : '#667eea'}; font-weight: 700; font-size: 16px;">${goal.progress_pct}%</span>
      </div>
      <div style="background: #e5e7eb; border-radius: 999px; height: 10px; overflow: hidden; box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);">
        <div style="
          background: ${isCompleted ? 'linear-gradient(90deg, #10b981 0%, #059669 100%)' : 'linear-gradient(90deg, #667eea 0%, #764ba2 100%)'}; 
          height: 100%; 
          width: ${progressWidth}%; 
          transition: width 0.5s ease;
          box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        "></div>
      </div>
    </div>

    <div style="background: ${isCompleted ? 'rgba(16, 185, 129, 0.1)' : '#f9fafb'}; padding: 10px; border-radius: 8px; display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 12px;">
      <div>
        <div style="color: #6b7280; margin-bottom: 2px;"><i class="fas fa-calendar"></i> Deadline</div>
        <div style="color: #374151; font-weight: 600;">${daysText}</div>
      </div>
      ${!isCompleted && remaining > 0 ? `
      <div>
        <div style="color: #6b7280; margin-bottom: 2px;"><i class="fas fa-coins"></i> Perlu per bulan</div>
        <div style="color: #374151; font-weight: 600;">${monthlyNeeded > 0 ? window.formatCurrency(monthlyNeeded) : '-'}</div>
      </div>
      ` : `
      <div>
        <div style="color: #047857; margin-bottom: 2px;"><i class="fas fa-trophy"></i> Status</div>
        <div style="color: #047857; font-weight: 600;">Target Tercapai!</div>
      </div>
      `}
    </div>
  `;
  return card;
}

function clearGoalForm() {
  document.getElementById('goal-name').value = '';
  document.getElementById('goal-target').value = '';
  document.getElementById('goal-date').value = '';
  const initialEl = document.getElementById('goal-initial');
  if (initialEl) initialEl.value = '';
  document.getElementById('goal-desc').value = '';
  const msgEl = document.getElementById('goal-msg');
  if (msgEl) {
    msgEl.textContent = '';
    msgEl.className = 'small';
  }
}
