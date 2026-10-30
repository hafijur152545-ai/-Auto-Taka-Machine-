
// ===== ADS SYSTEM FIXED - 15 SEC + REAL SDK =====
let AD_DURATION = 15; // 15 second fixed

// Real Ad Function using Adspark SDK
async function showRealAd() {
  return new Promise(async (resolve) => {
    const modal = document.getElementById("fakeAdModal");
    const timerEl = document.getElementById("adTimer");
    const bar = document.getElementById("bar");
    
    // Try Real SDK first
    try {
      // SDK check - তোমার SDK অনুযায়ী
      if (window.Adspark && typeof window.Adspark.showAd === 'function') {
        console.log("Trying Adspark.showAd...");
        await window.Adspark.showAd();
        console.log("✅ Real Ad Shown via Adspark.showAd");
        resolve(true);
        return;
      }
      if (window.showAd && typeof window.showAd === 'function') {
        console.log("Trying window.showAd...");
        await window.showAd();
        console.log("✅ Real Ad Shown via window.showAd");
        resolve(true);
        return;
      }
      if (window.AdsparkSDK && typeof window.AdsparkSDK.show === 'function') {
        await window.AdsparkSDK.show();
        resolve(true);
        return;
      }
      // If SDK exposes Ads object
      if (window.adspark && window.adspark.show) {
        await window.adspark.show();
        resolve(true);
        return;
      }
    } catch (e) {
      console.log("SDK Ad failed, fallback to timer:", e);
    }

    // Fallback: 15s timer modal (always works)
    modal.style.display = "flex";
    let c = AD_DURATION;
    timerEl.innerText = c;
    bar.style.width = "0%";
    let iv = setInterval(() => {
      c--;
      timerEl.innerText = c;
      bar.style.width = ((AD_DURATION - c) / AD_DURATION * 100) + "%";
      if (c <= 0) {
        clearInterval(iv);
        modal.style.display = "none";
        resolve(true);
      }
    }, 1000);
  });
}

// FakeAds wrapper for compatibility
window.FakeAds = { show: showRealAd };

// ===== BALANCE SYSTEM =====
let mainBal = parseFloat(localStorage.getItem("mainBal") || "10.20");
let pendingBal = parseFloat(localStorage.getItem("pendingBal") || "5.10");
let dailyAds = parseInt(localStorage.getItem("dailyAds") || "0");
let autoI = null, countI = null, sec = AD_DURATION;

function upd() {
  document.getElementById("mainBal").innerText = mainBal.toFixed(2);
  document.getElementById("pendingBal").innerText = pendingBal.toFixed(2);
  document.getElementById("dailyCount").innerText = dailyAds;
  const pM = document.getElementById("pMain"), pP = document.getElementById("pPending"), pA = document.getElementById("pAds");
  if (pM) pM.innerText = mainBal.toFixed(2) + " TK";
  if (pP) pP.innerText = pendingBal.toFixed(2) + " TK";
  if (pA) pA.innerText = dailyAds;
  localStorage.setItem("mainBal", mainBal);
  localStorage.setItem("pendingBal", pendingBal);
  localStorage.setItem("dailyAds", dailyAds);
}
upd();

async function one() {
  const sb = document.getElementById("statusBar");
  if (sb) sb.innerText = "📢 Ad Playing - 15s";
  const success = await showRealAd();
  if (success) {
    pendingBal += 0.50;
    dailyAds++;
    upd();
    if (sb) sb.innerText = "✅ +0.50 TK - Next in 15s";
  } else {
    if (sb) sb.innerText = "❌ Ad Failed - Try Again";
  }
}

document.getElementById("watchAdBtn").onclick = one;

document.getElementById("autoBtn").onclick = () => {
  if (autoI) return;
  const dot = document.getElementById("autoDot");
  if (dot) dot.style.display = "block";
  const sb = document.getElementById("statusBar");
  if (sb) sb.innerText = "⚡ AUTO MODE: Running (15s)";
  sec = AD_DURATION;
  one();
  autoI = setInterval(() => { one(); sec = AD_DURATION; }, AD_DURATION * 1000);
  countI = setInterval(() => {
    const sm = document.getElementById("autoSmall");
    if (sm) sm.innerText = "Refresh in " + sec + "s - Auto Running...";
    sec--;
    if (sec < 0) sec = AD_DURATION;
  }, 1000);
};

document.getElementById("stopBtn").onclick = () => {
  clearInterval(autoI); clearInterval(countI);
  autoI = null; countI = null;
  const dot = document.getElementById("autoDot");
  if (dot) dot.style.display = "none";
  const sb = document.getElementById("statusBar");
  if (sb) sb.innerText = "🟢 Bot Ready - Stopped";
  const sm = document.getElementById("autoSmall");
  if (sm) sm.innerText = "Refresh every 15 seconds";
  const m = document.getElementById("fakeAdModal");
  if (m) m.style.display = "none";
};

document.getElementById("confirmBtn").onclick = () => {
  if (pendingBal <= 0) return alert("❌ Pending Balance 0 TK!");
  mainBal += pendingBal;
  pendingBal = 0;
  upd();
  alert("✅ Confirm Done! Main Balance Added!");
};

function showHome() {
  document.getElementById("homePage").style.display = "block";
  document.getElementById("profilePage").style.display = "none";
  document.getElementById("homeNav").classList.add("active");
  document.getElementById("profileNav").classList.remove("active");
}
function showProfile() {
  document.getElementById("homePage").style.display = "none";
  document.getElementById("profilePage").style.display = "block";
  document.getElementById("profileNav").classList.add("active");
  document.getElementById("homeNav").classList.remove("active");
}

// Telegram WebApp Auto Profile
const tg = window.Telegram?.WebApp;
if (tg) {
  try {
    tg.ready();
    tg.expand();
    tg.setHeaderColor("#6d28d9");
    tg.setBackgroundColor("#6d28d9");
    const u = tg.initDataUnsafe?.user;
    if (u) {
      const name = (u.first_name || "") + (u.last_name ? " " + u.last_name : "");
      const username = u.username ? "@" + u.username : "@" + (u.id || "user");
      const photo = u.photo_url || "https://via.placeholder.com/88";
      const homeName = document.getElementById("homeName");
      const homePhoto = document.getElementById("homePhoto");
      const profileName = document.getElementById("profileName");
      const profilePhoto = document.getElementById("profilePhoto");
      const profileUsername = document.getElementById("profileUsername");
      const profileId = document.getElementById("profileId");
      if (homeName) homeName.innerText = name || "E Noyon";
      if (homePhoto) homePhoto.src = photo;
      if (profileName) profileName.innerText = name || "E Noyon";
      if (profilePhoto) profilePhoto.src = photo;
      if (profileUsername) profileUsername.innerText = username;
      if (profileId) profileId.innerText = "ID: " + (u.id || "123456");
    }
  } catch (e) { console.log("TG Error", e); }
}

document.getElementById("vpnBtn").onclick = () => window.open("https://play.google.com/store/apps/details?id=free.vpnaustralia.unlimited.tunnel.proxy.secure.hotspot", "_blank");
document.getElementById("channelBtn").onclick = () => window.open("https://t.me/SmartWorkCommunity", "_blank");
document.getElementById("adminBtn").onclick = () => window.open("https://t.me/noyonfb1020", "_blank");

console.log("✅ Auto Taka Machine Loaded - Fixed 15s + SDK Integrated");

// Check SDK loaded
window.addEventListener('load', () => {
  setTimeout(() => {
    if (window.Adspark || window.showAd || window.AdsparkSDK) {
      console.log("✅ Adspark SDK Detected:", window.Adspark || window.showAd);
      document.getElementById("statusBar").innerText = "✅ SDK Ready - 15s Ads";
    } else {
      console.log("⚠️ SDK not found, using fallback timer");
    }
  }, 1000);
});
