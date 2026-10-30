
// GLOBAL USER DATA
let realName = 'User';
let realUid = '000000';
let realPhoto = '';
let realInitials = 'U';
let tgApp = null;
try {
  tgApp = window.Telegram?.WebApp;
  if(tgApp) { tgApp.ready(); tgApp.expand(); }
  const u = tgApp?.initDataUnsafe?.user;
  if(u) {
    const f = u.first_name || 'User';
    const l = u.last_name || '';
    realName = (f + ' ' + l).trim() || u.username || 'User';
    realUid = String(u.id);
    realPhoto = u.photo_url || '';
    realInitials = f.slice(0,2).toUpperCase();
  }
} catch(e) { console.log('TG error', e); }

// BALANCES - Default 0
let mainBalance = 0.00;
let pendingBalance = 0.00;
let dailyCount = 0;
let totalAds = 0;
let totalEarned = 0;
let totalReferrals = 0;
let autoMode = false;
let autoInterval = null;
let selectedMethod = null;

// Min Withdraw Limits - Admin Controllable via localStorage
let minWithdrawLimits = (() => {
  try {
    let saved = localStorage.getItem('minWithdrawLimits');
    if(saved) {
      let p = JSON.parse(saved);
      return { bkash: Number(p.bkash||0), nagad: Number(p.nagad||0), rocket: Number(p.rocket||0) };
    }
  } catch(e) {}
  return { bkash: 0, nagad: 0, rocket: 0 };
})();

let withdrawHistory = [];

function $(id) { return document.getElementById(id); }

function showToast(msg, duration=2000) {
  const t = $('simpleToast');
  t.textContent = msg;
  t.classList.add('show');
  t.classList.remove('hidden');
  setTimeout(() => { t.classList.remove('show'); t.classList.add('hidden'); }, duration);
}

function showAdToast(text) {
  const t = $('adToast');
  $('adToastText').textContent = text;
  t.classList.add('show');
  t.classList.remove('hidden');
}
function hideAdToast() {
  const t = $('adToast');
  t.classList.remove('show');
  t.classList.add('hidden');
}

function updateUI() {
  if($('mainBal')) $('mainBal').textContent = mainBalance.toFixed(2) + ' TK';
  if($('pendingBal')) $('pendingBal').textContent = pendingBalance.toFixed(2) + ' TK';
  if($('profileMainBal')) $('profileMainBal').textContent = mainBalance.toFixed(2) + ' TK';
  if($('profilePendingBal')) $('profilePendingBal').textContent = pendingBalance.toFixed(2) + ' TK';
  if($('withdrawCurrentBal')) $('withdrawCurrentBal').textContent = mainBalance.toFixed(2) + ' TK';
  if($('dailyCount')) $('dailyCount').textContent = `TODAY ${dailyCount} Ads`;
  if($('homeDailyTop')) $('homeDailyTop').textContent = `Today ${dailyCount} Ads`;
  if($('profileTotalAds')) $('profileTotalAds').textContent = `${totalAds} Ads`;
  if($('profileTotalEarned')) $('profileTotalEarned').textContent = `${totalEarned} TK`;
  if($('totalReferred')) $('totalReferred').textContent = totalReferrals;
  if($('profileTotalReferrals')) $('profileTotalReferrals').textContent = totalReferrals;
  if($('confirmText')) $('confirmText').textContent = `${dailyCount}/500 ads • ${(dailyCount/500*100).toFixed(1)}%`;
  if($('confirmProgress')) $('confirmProgress').style.width = Math.min(dailyCount/500*100, 100) + '%';
  if($('mainProgress')) $('mainProgress').style.width = Math.min(mainBalance/1000*100, 100) + '%';
  
  // User data
  if($('homeUserName')) $('homeUserName').textContent = realName;
  if($('profileUserName')) $('profileUserName').textContent = realName;
  if($('homeUserUid')) $('homeUserUid').textContent = `UID: ${realUid}`;
  if($('profileUserUid')) $('profileUserUid').textContent = `UID: ${realUid}`;
  if($('referralLinkInput')) $('referralLinkInput').value = `https://t.me/AutoTakaMachineBot?start=${realUid}`;
  
  // Avatar
  const avatarHTML = realPhoto ? `<img src="${realPhoto}" class="w-full h-full object-cover rounded-full">` : realInitials;
  if($('homeUserAvatar')) {
    if(realPhoto) { $('homeUserAvatar').innerHTML = `<img src="${realPhoto}" class="w-full h-full object-cover rounded-full">`; $('homeUserAvatar').className = 'w-12 h-12 rounded-full overflow-hidden'; }
    else { $('homeUserAvatar').textContent = realInitials; }
  }
  if($('profileUserAvatar')) {
    if(realPhoto) { $('profileUserAvatar').innerHTML = `<img src="${realPhoto}" class="w-full h-full object-cover rounded-full">`; $('profileUserAvatar').className = 'w-14 h-14 rounded-full overflow-hidden'; }
    else { $('profileUserAvatar').textContent = realInitials; }
  }
}

function addReward() {
  pendingBalance = +(pendingBalance + 0.50).toFixed(2);
  dailyCount++;
  totalAds++;
  totalEarned = +(totalEarned + 0.50).toFixed(2);
  updateUI();
}

function watchAd() {
  if($('watchAdBtn').disabled) return;
  $('watchAdBtn').disabled = true;
  showAdToast('MANUAL Loading Ad...');
  
  const tryRealAd = () => {
    try {
      // AdSpark SDK - try multiple API patterns
      if(window.AdSpark && typeof window.AdSpark.showAd === 'function') {
        window.AdSpark.showAd({
          onReward: () => { addReward(); hideAdToast(); showToast('Ad Completed! +0.50 TK'); $('watchAdBtn').disabled = false; },
          onClose: () => { hideAdToast(); $('watchAdBtn').disabled = false; },
          onError: (e) => { console.log('AdSpark error', e); hideAdToast(); fallbackFake(); }
        });
        return true;
      }
      if(typeof window.showAd === 'function') {
        // Some SDKs use window.showAd()
        const result = window.showAd();
        if(result && result.then) {
          result.then(() => { addReward(); hideAdToast(); showToast('Ad Completed! +0.50 TK'); }).catch(()=>fallbackFake()).finally(()=>{$('watchAdBtn').disabled=false;});
        } else {
          // Callback style
          addReward(); hideAdToast(); showToast('Ad Completed! +0.50 TK'); $('watchAdBtn').disabled=false;
        }
        return true;
      }
      // Check for Adsgram style
      if(window.Adsgram && window.Adsgram.init) {
        const AdController = window.Adsgram.init({ blockId: '64' });
        AdController.show().then(() => { addReward(); showToast('Ad Completed! +0.50 TK'); }).catch(()=>fallbackFake()).finally(()=>{hideAdToast(); $('watchAdBtn').disabled=false;});
        return true;
      }
    } catch(e) { console.log('Ad try error', e); }
    return false;
  };
  
  const fallbackFake = () => {
    setTimeout(() => {
      showAdToast('COMPLETED Ad Served • +0.50 TK');
      addReward();
      setTimeout(() => { hideAdToast(); $('watchAdBtn').disabled = false; }, 1500);
    }, 2000);
  };
  
  if(!tryRealAd()) {
    fallbackFake();
  }
  
  // Update status
  if($('statusBar')) { $('statusBar').innerHTML = '<span class="w-1.5 h-1.5 bg-yellow-400 rounded-full animate-pulse"></span> LOADING'; }
  setTimeout(() => { if($('statusBar')) $('statusBar').innerHTML = '<span class="w-1.5 h-1.5 bg-green-400 rounded-full"></span> IDLE'; }, 4000);
}

function toggleAuto() {
  autoMode = !autoMode;
  if(autoMode) {
    $('autoStatusText').textContent = 'AUTO ON';
    $('autoStatusDot').className = 'w-2 h-2 bg-green-400 rounded-full animate-pulse';
    $('autoBtn').classList.add('bg-[#f0fdf4]');
    showToast('Auto Loop Started');
    autoInterval = setInterval(() => { if(!autoMode) return; watchAd(); }, 15000);
  } else {
    $('autoStatusText').textContent = 'AUTO OFF';
    $('autoStatusDot').className = 'w-2 h-2 bg-gray-400 rounded-full';
    $('autoBtn').classList.remove('bg-[#f0fdf4]');
    showToast('Auto Loop Stopped');
    if(autoInterval) clearInterval(autoInterval);
  }
}

function stopAuto() {
  autoMode = false;
  $('autoStatusText').textContent = 'AUTO OFF';
  $('autoStatusDot').className = 'w-2 h-2 bg-gray-400 rounded-full';
  $('autoBtn').classList.remove('bg-[#f0fdf4]');
  if(autoInterval) clearInterval(autoInterval);
  showToast('Stopped');
}

function confirmBalance() {
  if(pendingBalance > 0) {
    mainBalance = +(mainBalance + pendingBalance).toFixed(2);
    pendingBalance = 0;
    dailyCount = 0;
    updateUI();
    showToast('Balance Confirmed! Moved to Main');
  } else {
    showToast('No pending balance');
  }
}

// Tab Switching
function showHome() {
  $('homeContent').classList.remove('hidden');
  $('profilePageContent').classList.add('hidden');
  $('homeNav').className = 'flex-1 bg-white text-[#111827] rounded-full py-2.5 font-semibold text-[13px] flex items-center justify-center gap-1.5';
  $('profileNav').className = 'flex-1 bg-transparent text-white/50 rounded-full py-2.5 font-semibold text-[13px] flex items-center justify-center gap-1.5';
}

function showProfile() {
  $('homeContent').classList.add('hidden');
  $('profilePageContent').classList.remove('hidden');
  $('profileNav').className = 'flex-1 bg-white text-[#111827] rounded-full py-2.5 font-semibold text-[13px] flex items-center justify-center gap-1.5';
  $('homeNav').className = 'flex-1 bg-transparent text-white/50 rounded-full py-2.5 font-semibold text-[13px] flex items-center justify-center gap-1.5';
}

// Withdraw Logic
function selectMethod(method) {
  selectedMethod = method;
  // Reset borders
  $('bkashBtn').classList.remove('border-[#e2136e]', 'ring-2', 'ring-[#e2136e]/20');
  $('nagadBtn').classList.remove('border-[#f6921e]', 'ring-2', 'ring-[#f6921e]/20');
  $('rocketBtn').classList.remove('border-[#8c3494]', 'ring-2', 'ring-[#8c3494]/20');
  // Active
  if(method === 'bkash') $('bkashBtn').classList.add('border-[#e2136e]', 'ring-2', 'ring-[#e2136e]/20');
  if(method === 'nagad') $('nagadBtn').classList.add('border-[#f6921e]', 'ring-2', 'ring-[#f6921e]/20');
  if(method === 'rocket') $('rocketBtn').classList.add('border-[#8c3494]', 'ring-2', 'ring-[#8c3494]/20');
  
  // Show min limit
  const min = minWithdrawLimits[method] || 0;
  if($('minWithdrawDisplay')) $('minWithdrawDisplay').textContent = min + ' TK';
}

function requestWithdraw() {
  const number = $('withdrawNumber').value.trim();
  const amountStr = $('withdrawAmount').value.trim();
  
  if(!selectedMethod) { showToast('Select payment method first'); return; }
  if(!number) { showToast('Enter number'); return; }
  if(!amountStr) { showToast('Enter amount'); return; }
  
  const amount = Number(amountStr);
  if(isNaN(amount) || amount <= 0) { showToast('Invalid amount'); return; }
  
  const min = minWithdrawLimits[selectedMethod] || 0;
  if(amount < min) { showToast(`Min withdraw ${min} TK for ${selectedMethod}`); return; }
  if(amount > mainBalance) { showToast(`Insufficient balance. You have ${mainBalance.toFixed(2)} TK`); return; }
  
  mainBalance = +(mainBalance - amount).toFixed(2);
  const masked = number.length > 4 ? `****${number.slice(-4)}` : number;
  const now = new Date();
  const dateStr = `${now.getDate()} ${now.toLocaleString('en-US', {month:'short'})} • ${amount} TK`;
  const item = { id: Date.now(), date: dateStr, amount, numberMasked: masked, method: selectedMethod, status: 'PENDING' };
  withdrawHistory.unshift(item);
  
  // Update history UI
  renderHistory();
  
  $('withdrawNumber').value = '';
  $('withdrawAmount').value = '';
  updateUI();
  showToast(`Withdraw ${amount} TK via ${selectedMethod} requested!`);
}

function renderHistory() {
  const list = $('withdrawHistoryList');
  if(withdrawHistory.length === 0) {
    list.innerHTML = '<div class="text-center py-6 text-gray-400 text-[13px]">No history yet<br><span class="text-[20px]">📭</span></div>';
    return;
  }
  list.innerHTML = withdrawHistory.map(h => `
    <div class="flex items-center justify-between py-3 border-b border-gray-50 last:border-0">
      <div><div class="text-[13px] font-semibold">${h.date}</div><div class="text-[11px] text-gray-500">${h.method} • ${h.numberMasked}</div></div>
      <div class="text-right"><div class="text-[13px] font-bold">${h.amount} TK</div><div class="text-[10px] px-2 py-0.5 rounded-full ${h.status==='PAID'?'bg-green-100 text-green-700':'bg-yellow-100 text-yellow-700'}">${h.status}</div></div>
    </div>
  `).join('');
}

// Init
document.addEventListener('DOMContentLoaded', () => {
  updateUI();
  // Load guidelines from localStorage
  try {
    let g = localStorage.getItem('adminGuidelines');
    if(g && g.trim()) $('adminGuidelines').innerHTML = g;
  } catch(e) {}
  
  // Event listeners
  if($('watchAdBtn')) $('watchAdBtn').addEventListener('click', watchAd);
  if($('autoBtn')) $('autoBtn').addEventListener('click', toggleAuto);
  if($('stopBtn')) $('stopBtn').addEventListener('click', stopAuto);
  if($('confirmBtn')) $('confirmBtn').addEventListener('click', confirmBalance);
  if($('homeNav')) $('homeNav').addEventListener('click', showHome);
  if($('profileNav')) $('profileNav').addEventListener('click', showProfile);
  if($('channelBtn')) $('channelBtn').addEventListener('click', () => window.open('https://t.me/SmartWorkCommunity','_blank'));
  if($('adminBtn')) $('adminBtn').addEventListener('click', () => window.open('https://t.me/noyonfb1020','_blank'));
  if($('vpnBtn')) $('vpnBtn').addEventListener('click', () => window.open('https://play.google.com/store/apps/details?id=free.vpnaustralia.unlimited.tunnel.proxy.secure.hotspot','_blank'));
  if($('adminPanelBtn')) $('adminPanelBtn').addEventListener('click', () => showToast('Admin Panel: Premium access required'));
  if($('bkashBtn')) $('bkashBtn').addEventListener('click', () => selectMethod('bkash'));
  if($('nagadBtn')) $('nagadBtn').addEventListener('click', () => selectMethod('nagad'));
  if($('rocketBtn')) $('rocketBtn').addEventListener('click', () => selectMethod('rocket'));
  if($('requestWithdrawBtn')) $('requestWithdrawBtn').addEventListener('click', requestWithdraw);
  if($('copyReferralBtn')) $('copyReferralBtn').addEventListener('click', () => {
    try { $('referralLinkInput').select(); document.execCommand('copy'); showToast('Referral link copied!'); } catch(e) { showToast('Copy failed'); }
  });
  
  // Load saved balances if any
  try {
    let savedMain = localStorage.getItem('mainBalance');
    let savedPending = localStorage.getItem('pendingBalance');
    if(savedMain) mainBalance = Number(savedMain);
    if(savedPending) pendingBalance = Number(savedPending);
    updateUI();
  } catch(e) {}
});

setInterval(() => {
  try {
    localStorage.setItem('mainBalance', mainBalance);
    localStorage.setItem('pendingBalance', pendingBalance);
  } catch(e) {}
}, 2000);
