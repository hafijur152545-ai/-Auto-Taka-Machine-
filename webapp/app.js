
// ===== CONFIG - 15-18 SEC =====
const AD_DURATION = 15; // চাইলে 18 করে দাও
let mainBal = parseFloat(localStorage.getItem("mainBal") || "0.00");
let pendingBal = parseFloat(localStorage.getItem("pendingBal") || "0.00");
let todayAds = parseInt(localStorage.getItem("todayAds") || "0");
let totalAds = parseInt(localStorage.getItem("totalAds") || "0");
let autoI = null, countI = null;

function upd() {
  document.getElementById("mainBal").innerText = mainBal.toFixed(2) + " TK";
  document.getElementById("pendingBal").innerText = pendingBal.toFixed(2) + " TK";
  const pMain = document.getElementById("pMainBal"), pPend = document.getElementById("pPendingBal");
  if(pMain) pMain.innerText = mainBal.toFixed(2) + " TK";
  if(pPend) pPend.innerText = pendingBal.toFixed(2) + " TK";
  document.getElementById("todayCount").innerText = todayAds;
  document.getElementById("pTotalAds").innerText = totalAds + " Ads";
  document.getElementById("todayPercent").innerText = (todayAds/500*100).toFixed(1) + "%";
  document.getElementById("pTotalPercent").innerText = (todayAds/500*100).toFixed(1) + "% of daily";
  document.getElementById("todayProgress").style.width = Math.min(todayAds/500*100,100) + "%";
  document.getElementById("confirmText").innerText = totalAds + "/500 ads • +3.2%";
  document.getElementById("wBal").innerText = mainBal.toFixed(2) + " TK";
  localStorage.setItem("mainBal", mainBal);
  localStorage.setItem("pendingBal", pendingBal);
  localStorage.setItem("todayAds", todayAds);
  localStorage.setItem("totalAds", totalAds);
}
upd();

// Toast helpers like video
function showToastLoading() {
  const toast = document.getElementById("adToast");
  const load = document.getElementById("adToastLoading");
  const succ = document.getElementById("adToastSuccess");
  load.style.display = "flex";
  succ.style.display = "none";
  toast.classList.remove("hidden");
}
function showToastSuccess() {
  const load = document.getElementById("adToastLoading");
  const succ = document.getElementById("adToastSuccess");
  const banner = document.getElementById("adCompletedBanner");
  load.style.display = "none";
  succ.style.display = "flex";
  banner.classList.remove("hidden");
  document.getElementById("topStatus").innerText = "Ad Completed! +0.50 TK";
  setTimeout(() => {
    document.getElementById("adToast").classList.add("hidden");
    banner.classList.add("hidden");
    document.getElementById("topStatus").innerText = "BOT READY";
  }, 2500);
}
function hideToast() {
  document.getElementById("adToast").classList.add("hidden");
}

// Real Ad with SDK + 15-18 sec timer like video
async function showRealAd() {
  showToastLoading();
  document.getElementById("autoStatus").innerText = "LOADING";
  
  // Try Real SDK first
  let realAdShown = false;
  try {
    if (window.Adspark && typeof window.Adspark.showAd === 'function') {
      console.log("Calling Adspark.showAd...");
      await window.Adspark.showAd();
      realAdShown = true;
    } else if (window.showAd && typeof window.showAd === 'function') {
      await window.showAd();
      realAdShown = true;
    } else if (window.AdsparkSDK && window.AdsparkSDK.show) {
      await window.AdsparkSDK.show();
      realAdShown = true;
    }
  } catch(e) {
    console.log("Real Ad failed, using timer", e);
  }

  // 15-18 sec timer (video style - Manual Loading)
  return new Promise((resolve) => {
    let elapsed = 0;
    const interval = setInterval(() => {
      elapsed++;
      // Update toast text with countdown like video had?
      if (elapsed >= AD_DURATION) {
        clearInterval(interval);
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
    showToastSuccess();
    document.getElementById("autoStatus").innerText = "IDLE";
  } else {
    hideToast();
    document.getElementById("autoStatus").innerText = "FAILED";
  }
}

document.getElementById("watchAdBtn").onclick = oneAd;

document.getElementById("autoBtn").onclick = () => {
  if (autoI) return;
  document.getElementById("autoOffCard").innerHTML = "<small>AUTO ON</small><div class='off-dot' style='background:#22c55e;border-color:#22c55e'></div>";
  document.getElementById("autoStatus").innerText = "ACTIVE";
  oneAd();
  autoI = setInterval(oneAd, AD_DURATION * 1000);
};

document.getElementById("stopBtn").onclick = () => {
  clearInterval(autoI);
  autoI = null;
  document.getElementById("autoOffCard").innerHTML = "<small>AUTO OFF</small><div class='off-dot'></div>";
  document.getElementById("autoStatus").innerText = "IDLE";
  hideToast();
  document.getElementById("topStatus").innerText = "BOT READY";
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
  document.querySelector(".phone").style.display = "block";
  document.getElementById("profilePage").style.display = "none";
  document.getElementById("homeNav").classList.add("bn-active");
  document.getElementById("profileNav").classList.remove("bn-active");
}
function showProfile() {
  document.querySelector(".phone").style.display = "none";
  document.getElementById("profilePage").style.display = "block";
  document.getElementById("profileNav").classList.add("bn-active");
  document.getElementById("homeNav").classList.remove("bn-active");
}

// Telegram Profile
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
  } catch(e){console.log(e)}
}

// Links
document.getElementById("channelBtn").onclick = () => window.open("https://t.me/SmartWorkCommunity","_blank");
document.getElementById("adminBtn").onclick = () => window.open("https://t.me/noyonfb1020","_blank");
document.getElementById("vpnBtn").onclick = () => window.open("https://play.google.com/store/apps/details?id=free.vpnaustralia.unlimited.tunnel.proxy.secure.hotspot","_blank");
document.getElementById("copyRef").onclick = () => {
  navigator.clipboard.writeText(document.getElementById("refLink").value);
  alert("Copied!");
};

console.log("✅ Auto Taka Machine V2.4 - Video Design + 15s Ad + SDK");
setTimeout(() => {
  if (window.Adspark || window.showAd) {
    console.log("✅ SDK Ready");
    document.getElementById("topStatus").innerText = "BOT READY - SDK OK";
  }
}, 1000);
