// ===== AUTO TAKA MACHINE - FINAL UPDATED BY YOUR REQUIREMENT =====
const AD_DURATION = 17; // Ad open হওয়ার মুহূর্ত থেকে 17s পর auto close
const LOAD_MANUAL = 2; // Manual Watch বাটনে 2s loading
const LOAD_AFTER_AD = 1; // Ad থেকে বের হওয়ার পর 1s loading -> Balance Pending
const LOAD_NEXT_AUTO = 2; // Auto Loop এ পরের Ad এর আগে 2s loading

let mainBal = parseFloat(localStorage.getItem("mainBal") || "0.00");
let pendingBal = parseFloat(localStorage.getItem("pendingBal") || "0.00");
let todayAds = parseInt(localStorage.getItem("todayAds") || "0");
let totalAds = parseInt(localStorage.getItem("totalAds") || "0");
let autoRunning = false;

function upd() {
  const g = id => document.getElementById(id);
  if(g("mainBal")) g("mainBal").innerText = mainBal.toFixed(2) + " TK";
  if(g("pendingBal")) g("pendingBal").innerText = pendingBal.toFixed(2) + " TK";
  if(g("pMainBal")) g("pMainBal").innerText = mainBal.toFixed(2) + " TK";
  if(g("pPendingBal")) g("pPendingBal").innerText = pendingBal.toFixed(2) + " TK";
  if(g("todayCount")) g("todayCount").innerText = todayAds;
  if(g("pTotalAds")) g("pTotalAds").innerText = totalAds + " Ads";
  if(g("todayPercent")) g("todayPercent").innerText = (todayAds/500*100).toFixed(1) + "%";
  if(g("pTotalPercent")) g("pTotalPercent").innerText = (todayAds/500*100).toFixed(1) + "% of daily";
  if(g("todayProgress")) g("todayProgress").style.width = Math.min(todayAds/500*100,100) + "%";
  if(g("confirmText")) g("confirmText").innerText = totalAds + "/500 ads • +3.2%";
  if(g("wBal")) g("wBal").innerText = mainBal.toFixed(2) + " TK";
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
  }, 1500);
}
function hideToast() {
  const t = document.getElementById("adToast");
  if(t) t.classList.add("hidden");
}

// ===== 17s পর অটো করস ক্লিক করার ফাংশন =====
function autoClickCross() {
  console.log("Trying auto close ad after 17s...");
  // Adspark / Monetag এর X বাটন গুলো
  const selectors = [
    '[class*="close"]', '[id*="close"]', 
    '.adspark-close', '.adspark__close', 
    'button.close', '.close-button',
    '[aria-label="Close"]', '[aria-label="close"]',
    '.monetag-close', '#monetag-close'
  ];
  
  // 1. চেষ্টা করো X বাটন ক্লিক করতে
  for(let sel of selectors){
    try {
      const btns = document.querySelectorAll(sel);
      for(let b of btns){
        if(b && b.offsetParent !== null){ // visible check
          b.click();
          console.log("Auto clicked close:", sel);
          return true;
        }
      }
    } catch(e){}
  }
  
  // 2. যদি না পায়, Adspark SDK এর close ফাংশন থাকলে কল করো
  try {
    if(window.closeAdspark) window.closeAdspark();
    if(window.Adspark && window.Adspark.close) window.Adspark.close();
  } catch(e){}
  
  // 3. শেষ চেষ্টা - কোনো overlay থাকলে সরিয়ে দাও
  const toast = document.getElementById("adToast");
  // Ad toast টা আলাদা, ওইটা থাকবে, কিন্তু বাইরের popup সরাবে
  
  // Adspark এর iframe গুলো খুঁজে বন্ধ করার চেষ্টা
  document.querySelectorAll('iframe').forEach(frame => {
    try{
      const src = frame.src || "";
      if(src.includes("ads") || src.includes("spark") || src.includes("monetag") || src.includes("propeller")){
        // frame.style.display = "none";
      }
    }catch(e){}
  });
  
  return true;
}

// ===== REAL AD - 17s por auto close =====
async function showRealAd() {
  showToastLoading();
  const autoStatus = document.getElementById("autoStatus");
  if(autoStatus) autoStatus.innerText = "LOADING AD";
  
  const tg = window.Telegram?.WebApp;
  const userId = tg?.initDataUnsafe?.user?.id || 0;

  // Adspark show
  try {
    if (typeof showAdspark === 'function') {
      showAdspark({ ymid: userId }).catch(()=>{});
    } else if (typeof showAdsparkPopup === 'function') {
      showAdsparkPopup({ ymid: userId }).catch(()=>{});
    }
  } catch(e){ console.log(e); }

  // 17 second timer - er por auto cross click + ber hobe
  return new Promise((resolve) => {
    let elapsed = 0;
    const interval = setInterval(() => {
      elapsed++;
      if(autoStatus) autoStatus.innerText = `AD ${elapsed}/${AD_DURATION}s`;
      
      if (elapsed >= AD_DURATION) {
        clearInterval(interval);
        autoClickCross(); // 17s পর অটো X ক্লিক
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
    
    // Ad theke ber howar por 1s loading - tomar dabi moto Balance Pending e jabe
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

// ===== Watch Ad - 2s Loading er por Ad e jabe =====
document.getElementById("watchAdBtn").onclick = async () => {
  if(autoRunning) return alert("Auto Loop চলছে, আগে Stop করো ভাই");
  
  const top = document.getElementById("topStatus");
  const autoStatus = document.getElementById("autoStatus");
  
  // 2 second manual loading - tomar dabi
  if(top) top.innerText = "Ads Loading Manual...";
  if(autoStatus) autoStatus.innerText = "LOADING 2s";
  showToastLoading();
  
  await delay(LOAD_MANUAL * 1000);
  
  if(top) top.innerText = "Opening Ad...";
  await oneAd();
};

// ===== AUTO LOOP - Stop na chaple choltei thakbe =====
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
    
    // Auto te sathe sathe Ad e niye jabe - kono 2s delay na
    await oneAd();
    if(!autoRunning) break;
    
    // Next ad er age 2s loading
    if(top) top.innerText = "Loading Next Ad...";
    if(autoStatus) autoStatus.innerText = "LOADING NEXT...";
    await delay(LOAD_NEXT_AUTO * 1000);
    
    if(!autoRunning) break;
    if(top) top.innerText = "BOT READY";
  }
};

document.getElementById("stopBtn").onclick = () => {
  autoRunning = false;
  const offCard = document.getElementById("autoOffCard");
  if(offCard) offCard.innerHTML = "<small>AUTO OFF</small><div class='off-dot'></div>";
  const autoStatus = document.getElementById("autoStatus");
  if(autoStatus) autoStatus.innerText = "IDLE";
  hideToast();
  const top = document.getElementById("topStatus");
  if(top) top.innerText = "BOT READY - STOPPED";
};

document.getElementById("confirmBtn").onclick = () => {
  if (pendingBal <= 0) return alert("❌ No pending balance!");
  if (totalAds < 1) return alert("Watch at least 1 ad!");
  mainBal += pendingBal;
  pendingBal = 0;
  upd();
  alert("✅ Confirmed! Added to Main Balance");
};

function showHome() {
  const phone = document.querySelector(".phone");
  const profile = document.getElementById("profilePage");
  if(phone) phone.style.display = "block";
  if(profile) profile.style.display = "none";
  document.getElementById("homeNav")?.classList.add("bn-active");
  document.getElementById("profileNav")?.classList.remove("bn-active");
}
function showProfile() {
  document.querySelector(".phone").style.display = "none";
  document.getElementById("profilePage").style.display = "block";
  document.getElementById("homeNav")?.classList.remove("bn-active");
  document.getElementById("profileNav")?.classList.add("bn-active");
}
window.showHome = showHome;
window.showProfile = showProfile;

const tg = window.Telegram?.WebApp;
if (tg) {
  try {
    tg.ready(); tg.expand();
    const u = tg.initDataUnsafe?.user;
    if (u) {
      const name = (u.first_name || "") + (u.last_name ? " " + u.last_name : "");
      const initial = (u.first_name?.[0] || "A") + (u.last_name?.[0] || "M");
      document.getElementById("userName").innerText = name || "Alex Morgan";
      document.getElementById("pUserName").innerText = name || "Alex Morgan";
      document.getElementById("avatarInitial").innerText = initial.toUpperCase();
      document.getElementById("pAvatarInitial").innerText = initial.toUpperCase();
      document.getElementById("userId").innerText = u.id || "000000";
      document.getElementById("pUserId").innerText = u.id || "000000";
    }
  } catch(e){}
}

document.getElementById("channelBtn").onclick = () => window.open("https://t.me/SmartWorkCommunity","_blank");
document.getElementById("adminBtn").onclick = () => window.open("https://t.me/noyonfb1020","_blank");
document.getElementById("vpnBtn").onclick = () => window.open("https://play.google.com/store/apps/details?id=free.vpnaustralia.unlimited.tunnel.proxy.secure.hotspot","_blank");
document.getElementById("copyRef").onclick = () => {
  const ref = document.getElementById("refLink");
  if(ref) navigator.clipboard.writeText(ref.value);
  alert("Copied!");
};

console.log("✅ Auto Taka Machine FINAL V3 - 17s Auto Cross Click + 2s Manual Load + 1s Balance Load + Loop till Stop");
setTimeout(() => {
  if (typeof showAdspark === 'function') {
    const top = document.getElementById("topStatus");
    if(top) top.innerText = "BOT READY - SDK OK";
  }
}, 1500);
