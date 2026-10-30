// ===== CONFIG - 15-18 SEC =====
const AD_DURATION = 15;
let mainBal = parseFloat(localStorage.getItem("mainBal") || "0.00");
let pendingBal = parseFloat(localStorage.getItem("pendingBal") || "0.00");
let todayAds = parseInt(localStorage.getItem("todayAds") || "0");
let totalAds = parseInt(localStorage.getItem("totalAds") || "0");
let autoI = null;

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
function hideToast() { document.getElementById("adToast").classList.add("hidden"); }

// ===== FIXED ADS FUNCTION - AdSpark er asol code =====
async function showRealAd() {
  showToastLoading();
  document.getElementById("autoStatus").innerText = "LOADING";
  const tg = window.Telegram?.WebApp;
  const userId = tg?.initDataUnsafe?.user?.id || 0;

  try {
    // AdSpark er official function
    if (typeof showAdspark === 'function') {
      await showAdspark({ ymid: userId });
      return true;
    } else if (typeof showAdsparkPopup === 'function') {
      await showAdsparkPopup({ ymid: userId });
      return true;
    } else {
      console.log("SDK not ready yet, using timer");
      // SDK load na hole 2 sec wait kore timer e jabe
      await new Promise(r => setTimeout(r, 2000));
      return true;
    }
  } catch(e) {
    console.log("No ad available", e);
    hideToast();
    document.getElementById("autoStatus").innerText = "NO AD";
    document.getElementById("topStatus").innerText = "No Ad - Try Later";
    setTimeout(()=>{ document.getElementById("topStatus").innerText = "BOT READY"; }, 2000);
    return false;
  }
}

async function oneAd() {
  const success = await showRealAd();
  if (success) {
    pendingBal += 0.50;
    todayAds++;
    totalAds++;
    upd();
    showToastSuccess();
    document.getElementById("autoStatus").innerText
