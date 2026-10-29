
window.FakeAds={show:()=>new Promise(res=>{
  const m=document.getElementById("fakeAdModal"), t=document.getElementById("adTimer"), b=document.getElementById("bar");
  m.style.display="flex"; let c=3; t.innerText=c; b.style.width="0%";
  let iv=setInterval(()=>{c--; t.innerText=c; b.style.width=((3-c)/3*100)+"%"; if(c<=0){clearInterval(iv); m.style.display="none"; res(true);}},1000);
})};
let mainBal=10.20, pendingBal=5.10, dailyAds=parseInt(localStorage.getItem("dailyAds")||"0"), autoI=null, countI=null, sec=15;
function upd(){
  document.getElementById("mainBal").innerText=mainBal.toFixed(2);
  document.getElementById("pendingBal").innerText=pendingBal.toFixed(2);
  document.getElementById("dailyCount").innerText=dailyAds;
  document.getElementById("pMain").innerText=mainBal.toFixed(2)+" TK";
  document.getElementById("pPending").innerText=pendingBal.toFixed(2)+" TK";
  document.getElementById("pAds").innerText=dailyAds;
  localStorage.setItem("dailyAds",dailyAds);
}
upd();
async function one(){document.getElementById("statusBar").innerText="Loop Active - Ad Playing"; await window.FakeAds.show(); pendingBal+=0.50; dailyAds++; upd(); document.getElementById("statusBar").innerText="Loop Active - Next in 15s";}
document.getElementById("watchAdBtn").onclick=one;
document.getElementById("autoBtn").onclick=()=>{
  if(autoI) return; document.getElementById("autoDot").style.display="block";
  document.getElementById("statusBar").innerText="AUTO MODE: Loop Active"; sec=15; one();
  autoI=setInterval(()=>{one(); sec=15;},15000);
  countI=setInterval(()=>{document.getElementById("autoSmall").innerText="Refresh in "+sec+"s - Auto Running..."; sec--; if(sec<0) sec=15;},1000);
};
document.getElementById("stopBtn").onclick=()=>{
  clearInterval(autoI); clearInterval(countI); autoI=null; countI=null;
  document.getElementById("autoDot").style.display="none";
  document.getElementById("statusBar").innerText="Bot Ready - Stopped";
  document.getElementById("autoSmall").innerText="Refresh every 15 seconds";
  document.getElementById("fakeAdModal").style.display="none";
};
document.getElementById("confirmBtn").onclick=()=>{if(pendingBal<=0) return alert("Pending nai"); mainBal+=pendingBal; pendingBal=0; upd(); alert("Confirm Done!");};
function showHome(){document.getElementById("homePage").style.display="block"; document.getElementById("profilePage").style.display="none"; document.getElementById("homeNav").classList.add("active"); document.getElementById("profileNav").classList.remove("active");}
function showProfile(){document.getElementById("homePage").style.display="none"; document.getElementById("profilePage").style.display="block"; document.getElementById("profileNav").classList.add("active"); document.getElementById("homeNav").classList.remove("active");}
// Telegram Auto Profile
const tg=window.Telegram?.WebApp;
if(tg){tg.ready(); tg.expand(); const u=tg.initDataUnsafe?.user; if(u){const name=u.first_name+(u.last_name?" "+u.last_name:""); const username=u.username?"@"+u.username:"@no_username"; const photo=u.photo_url||document.getElementById("homePhoto").src; document.getElementById("homeName").innerText=name; document.getElementById("homePhoto").src=photo; document.getElementById("profileName").innerText=name; document.getElementById("profilePhoto").src=photo; document.getElementById("profileUsername").innerText=username; document.getElementById("profileId").innerText="ID: "+u.id;}}
// === YOUR LINKS ===
document.getElementById("vpnBtn").onclick=()=>window.open("https://play.google.com/store/apps/details?id=free.vpnaustralia.unlimited.tunnel.proxy.secure.hotspot","_blank");
document.getElementById("channelBtn").onclick=()=>window.open("https://t.me/SmartWorkCommunity","_blank");
document.getElementById("adminBtn").onclick=()=>window.open("https://t.me/noyonfb1020","_blank");
