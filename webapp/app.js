// ===== CONFIG - UPDATED BY YOUR REQUIREMENT =====
const AD_DURATION = 17; // ভাই তুমি বলছো 17s পর অটো বের হবে
const LOAD_MANUAL = 2; // Manual Watch বাটনে 2s লোডিং
const LOAD_AFTER_AD = 1; // Ad থেকে বের হওয়ার পর 1s লোডিং
const LOAD_NEXT_AUTO = 2; // Auto Loop এ পরের Ad এর আগে 2s লোডিং
let mainBal = parseFloat(localStorage.getItem("mainBal") || "0.00");
let pendingBal = parseFloat(localStorage.getItem("pendingBal") || "0.00");
let todayAds = parseInt(localStorage.getItem("todayAds") || "0");
let totalAds = parseInt(localStorage.getItem("totalAds") || "0");
let autoI = null;
let autoRunning = false;

function upd() {
  const el = (id) => document.getElementById(id);
  if(el("mainBal")) el("mainBal").innerText = mainBal.toFixed(2) + " TK";
  if(el("pendingBal")) el("pendingBal").innerText = pendingBal.toFixed(2) + " TK";
  const pMain = el("pMainBal"), pPend = el("pPendingBal");
  if(pMain) pMain.innerText = mainBal.toFixed(2) + " TK";
  if(pPend) pPend.innerText = pendingBal.toFixed(2) + " TK";
  if(el("todayCount")) el("todayCount").innerText = todayAds;
  if(el("pTotalAds")) el("pTotalAds").innerText = totalAds + " Ads";
  if(el("todayPercent")) el("todayPercent").innerText = (todayAds/500*100).toFixed(1) + "%";
  if(el("pTotalPercent")) el("pTotalPercent").innerText = (todayAds/500*100).toFixed(1) + "% of daily";
  if(el("todayProgress")) el("todayProgress").style.width = Math.min(todayAds/500*100,100) + "%";
  if(el("confirmText")) el("confirmText").innerText = totalAds + "/500 ads \u2022 +3.2%";
  if(el("wBal")) el("wBal").innerText = mainBal.toFixed(2) + " TK";
  localStorage.setItem("mainBal", mainBal);
  localStorage.setItem("pendingBal", pendingBal);
  localStorage.setItem("todayAds", todayAds);
  localStorage.setItem("totalAds", totalAds);
}
upd();

function delay(ms){ return new Promise(r => setTimeout(r, ms)); }

function showToastLoading() {
  const toast = document.getElementById("adToast");
  const load = document.getElementById("adToastLoading");
  const succ = document.getElementById("adToastSuccess");
  if(!toast) return;
  if(load) load.style.display = "flex";
  if(succ) succ.style.display = "none";
  toast.classList.remove("hidden");
}
function showToastSuccess() {
  const load = document.getElementById("adToastLoading");
  const succ = document.getElementById("adToastSuccess");
  const banner = document.getElementById("adCompletedBanner");
  if(load) load.style.display = "none";
  if(succ) succ.style.display = "flex";
  if(banner) banner.classList.remove("hidden");
  const top = document.getElementById("topStatus");
  if(top) top.innerText = "Ad Completed! +0.50 TK";
  setTimeout(() => {
    const t = document.getElementById("adToast");
    if(t) t.classList.add("hidden");
    if(banner) banner.classList.add("hidden");
  }, 2000);
}
function hideToast() {
  const t = document.getElementById("adToast");
  if(t) t.classList.add("hidden");
}

// ===== REAL AD - 17 sec por auto close (No need X click) =====
async function showRealAd() {
  showToastLoading();
  const autoStatus = document.getElementById("autoStatus");
  if(autoStatus) autoStatus.innerText = "LOADING";
  const tg = window.Telegram?.WebApp;
  const userId = tg?.initDataUnsafe?.user?.id || 0;

  try {
    if (typeof showAdspark === 'function') {
      showAdspark({ ymid: userId }).catch(()=>{});
    } else if (typeof showAdsparkPopup === 'function') {
      showAdsparkPopup({ ymid: userId }).catch(()=>{});
    }
  } catch(e){}

  return new Promise((resolve) => {
    let elapsed = 0;
    const interval = setInterval(() => {
      elapsed++;
      if(autoStatus) autoStatus.innerText = `ADS ${elapsed}/${AD_DURATION}s`;
      const timerEl = document.getElementById("adTimer");
      if(timerEl) timerEl.innerText = `00:${String(AD_DURATION - elapsed).padStart(2,'0')}`;
      
      if (elapsed >= AD_DURATION) {
        clearInterval(interval);
        // Auto close - cross auto click er moto
        resolve(true);
      }
    }, 1000);
  });
}

async function oneAd() {
  const success = await showRealAd();
  if (success) {
    pendingBal += 0.50;
    todayAds++;
    totalAds++;
    upd();
    
    // Ad theke ber howar por 1 sec loading - tomar dabi moto
    const top = document.getElementById("topStatus");
    if(top) top.innerText = "Balance Pending...";
    await delay(LOAD_AFTER_AD * 1000);
    
    showToastSuccess();
    if(document.getElementById("autoStatus")) document.getElementById("autoStatus").innerText = "IDLE";
    if(top) top.innerText = "BOT READY";
    return true;
  }
  return false;
}

// ===== Watch Ad - EKHON 2 SEC LOADING ER POR AD E JABE =====
document.getElementById("watchAdBtn").onclick = async () => {
  if(autoRunning) return alert("Auto Loop চলছে, আগে Stop করো");
  
  const top = document.getElementById("topStatus");
  const autoStatus = document.getElementById("autoStatus");
  
  // 2 second manual loading - tomar dabi
  if(top) top.innerText = "Ads Loading Manual...";
  if(autoStatus) autoStatus.innerText = "LOADING MANUAL 2s";
  showToastLoading();
  
  await delay(LOAD_MANUAL * 1000);
  
  if(top) top.innerText = "Opening Ad...";
  await oneAd();
};

// ===== FINAL AUTO LOOP - STOP NA CHAPLE CHOLTEI THAKBE =====
document.getElementById("autoBtn").onclick = async () => {
  if (autoRunning) return;
  autoRunning = true;
  const offCard = document.getElementById("autoOffCard");
  if(offCard) offCard.innerHTML = "<small>AUTO ON</small><div class='off-dot' style='background:#22c55e;border-color:#22c55e'></div>";
  
  while(autoRunning) {
    const top = document.getElementById("topStatus");
    const autoStatus = document.getElementById("autoStatus");
    if(autoStatus) autoStatus.innerText = "ACTIVE";
    if(top) top.innerText = "Auto Ad Opening...";
    
    // Immediate ad open for Auto (no 2s delay for auto - as you said)
    await oneAd();
    if(!autoRunning) break;
    
    // Next ad er age 2 sec loading
    if(top) top.innerText = "Loading Next Ad...";
    if(autoStatus) autoStatus.innerText = "LOADING NEXT...";
    await delay(LOAD_NEXT_AUTO * 1000);
    
    if(!autoRunning) break;
    if(top) top.innerText = "BOT READY";
  }
};

document.getElementById("stopBtn").onclick = () => {
  autoRunning = false;
  clearInterval(autoI);
  autoI = null;
  const offCard = document.getElementById("autoOffCard");
  if(offCard) offCard.innerHTML = "<small>AUTO OFF</small><div class='off-dot'></div>";
  const autoStatus = document.getElementById("autoStatus");
  if(autoStatus) autoStatus.innerText = "IDLE";
  hideToast();
  const top = document.getElementById("topStatus");
  if(top) top.innerText = "BOT READY - STOPPED";
};

document.getElementById("confirmBtn").onclick = () => {
  if (pendingBal <= 0) return alert("\u274C No pending balance!");
  if (totalAds < 1) return alert("Watch at least 1 ad!");
  mainBal += pendingBal;
  pendingBal = 0;
  upd();
  alert("\u2705 Confirmed! Added to Main Balance");
};

function showHome() {
  const phone = document.querySelector(".phone");
  const profile = document.getElementById("profilePage");
  if(phone) phone.style.display = "block";
  if(profile) profile.style.display = "none";
  const hNav = document.getElementById("homeNav");
  const pNav = document.getElementById("profileNav");
  if(hNav) hNav.classList.add("bn-active");
  if(pNav) pNav.classList.remove("bn-active");
}
function showProfile() {
  const phone = document.querySelector(".phone");
  const profile = document.getElementById("profilePage");
  if(phone) phone.style.display = "none";
  if(profile) profile.style.display = "block";
  const hNav = document.getElementById("homeNav");
  const pNav = document.getElementById("profileNav");
  if(hNav) hNav.classList.remove("bn-active");
  if(pNav) pNav.classList.add("bn-active");
}

const tg = window.Telegram?.WebApp;
if (tg) {
  try {
    tg.ready(); tg.expand();
    const u = tg.initDataUnsafe?.user;
    if (u) {
      const name = (u.first_name || "") + (u.last_name ? " " + u.last_name : "");
      const initial = (u.first_name?.[0] || "A") + (u.last_name?.[0] || "M");
      const userName = document.getElementById("userName");
      const pUserName = document.getElementById("pUserName");
      const avInit = document.getElementById("avatarInitial");
      const pAvInit = document.getElementById("pAvatarInitial");
      const userIdEl = document.getElementById("userId");
      const pUserIdEl = document.getElementById("pUserId");
      if(userName) userName.innerText = name || "Alex Morgan";
      if(pUserName) pUserName.innerText = name || "Alex Morgan";
      if(avInit) avInit.innerText = initial.toUpperCase();
      if(pAvInit) pAvInit.innerText = initial.toUpperCase();
      if(userIdEl) userIdEl.innerText = u.id || "000000";
      if(pUserIdEl) pUserIdEl.innerText = u.id || "000000";
    }
  } catch(e){}
}

const channelBtn = document.getElementById("channelBtn");
if(channelBtn) channelBtn.onclick = () => window.open("https://t.me/SmartWorkCommunity","_blank");
const adminBtn = document.getElementById("adminBtn");
if(adminBtn) adminBtn.onclick = () => window.open("https://t.me/noyonfb1020","_blank");
const vpnBtn = document.getElementById("vpnBtn");
if(vpnBtn) vpnBtn.onclick = () => window.open("https://play.google.com/store/apps/details?id=free.vpnaustralia.unlimited.tunnel.proxy.secure.hotspot","_blank");
const copyRef = document.getElementById("copyRef");
if(copyRef) copyRef.onclick = () => {
  const ref = document.getElementById("refLink");
  if(ref) navigator.clipboard.writeText(ref.value);
  alert("Copied!");
};
console.log("\u2705 Auto Taka Machine UPDATED - 17s Auto Close + Manual 2s Load + 1s Balance Load + Loop till Stop");
setTimeout(() => {
  if (typeof showAdspark === 'function') {
    const top = document.getElementById("topStatus");
    if(top) top.innerText = "BOT READY - SDK OK";
  }
}, 1500);
