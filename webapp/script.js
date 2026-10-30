
window.FakeAds={show:()=>new Promise(res=>{
  const m=document.getElementById("fakeAdModal"), t=document.getElementById("adTimer"), b=document.getElementById("bar");
  m.style.display="flex"; let c=15; t.innerText=c; b.style.width="0%";
  let iv=setInterval(()=>{c--; t.innerText=c; b.style.width=((15-c)/15*100)+"%"; if(c<=0){clearInterval(iv); m.style.display="none"; res(true);}},1000);
})};

let mainBal=parseFloat(localStorage.getItem("mainBal")||"10.20"), pendingBal=parseFloat(localStorage.getItem("pendingBal")||"5.10"), dailyAds=parseInt(localStorage.getItem("dailyAds")||"0"), autoI=null, countI=null, sec=15;

function upd(){
  document.getElementById("mainBal").innerText=mainBal.toFixed(2);
  document.getElementById("pendingBal").innerText=pendingBal.toFixed(2);
  document.getElementById("dailyCount").innerText=dailyAds;
  const pM=document.getElementById("pMain"), pP=document.getElementById("pPending"), pA=document.getElementById("pAds");
  if(pM) pM.innerText=mainBal.toFixed(2)+" TK";
  if(pP) pP.innerText=pendingBal.toFixed(2)+" TK";
  if(pA) pA.innerText=dailyAds;
  localStorage.setItem("mainBal",mainBal);
  localStorage.setItem("pendingBal",pendingBal);
  localStorage.setItem("dailyAds",dailyAds);
}
upd();

async function one(){
  const sb=document.getElementById("statusBar");
  if(sb) sb.innerText="📢 Ad Playing - 15s";
  await window.FakeAds.show();
  pendingBal+=0.50;
  dailyAds++;
  upd();
  if(sb) sb.innerText="✅ +0.50 TK - Next in 15s";
}

document.getElementById("watchAdBtn").onclick=one;

document.getElementById("autoBtn").onclick=()=>{
  if(autoI) return;
  const dot=document.getElementById("autoDot");
  if(dot) dot.style.display="block";
  const sb=document.getElementById("statusBar");
  if(sb) sb.innerText="⚡ AUTO MODE: Running";
  sec=15;
  one();
  autoI=setInterval(()=>{one(); sec=15;},15000);
  countI=setInterval(()=>{
    const sm=document.getElementById("autoSmall");
    if(sm) sm.innerText="Refresh in "+sec+"s - Auto Running...";
    sec--;
    if(sec<0) sec=15;
  },1000);
};

document.getElementById("stopBtn").onclick=()=>{
  clearInterval(autoI); clearInterval(countI);
  autoI=null; countI=null;
  const dot=document.getElementById("autoDot");
  if(dot) dot.style.display="none";
  const sb=document.getElementById("statusBar");
  if(sb) sb.innerText="🟢 Bot Ready - Stopped";
  const sm=document.getElementById("autoSmall");
  if(sm) sm.innerText="Refresh every 15 seconds";
  const m=document.getElementById("fakeAdModal");
  if(m) m.style.display="none";
};

document.getElementById("confirmBtn").onclick=()=>{
  if(pendingBal<=0) return alert("❌ Pending Balance 0 TK!");
  mainBal+=pendingBal;
  pendingBal=0;
  upd();
  alert("✅ Confirm Done! Main Balance Added!");
};

function showHome(){
  document.getElementById("homePage").style.display="block";
  document.getElementById("profilePage").style.display="none";
  document.getElementById("homeNav").classList.add("active");
  document.getElementById("profileNav").classList.remove("active");
}
function showProfile(){
  document.getElementById("homePage").style.display="none";
  document.getElementById("profilePage").style.display="block";
  document.getElementById("profileNav").classList.add("active");
  document.getElementById("homeNav").classList.remove("active");
}

// Telegram WebApp Auto Profile
const tg=window.Telegram?.WebApp;
if(tg){
  try{
    tg.ready();
    tg.expand();
    tg.setHeaderColor("#6d28d9");
    tg.setBackgroundColor("#6d28d9");
    const u=tg.initDataUnsafe?.user;
    if(u){
      const name=(u.first_name||"")+(u.last_name?" "+u.last_name:"");
      const username=u.username?"@"+u.username:"@"+(u.id||"user");
      const photo=u.photo_url||"dev.jpg";
      const homeName=document.getElementById("homeName");
      const homePhoto=document.getElementById("homePhoto");
      const profileName=document.getElementById("profileName");
      const profilePhoto=document.getElementById("profilePhoto");
      const profileUsername=document.getElementById("profileUsername");
      const profileId=document.getElementById("profileId");
      if(homeName) homeName.innerText=name||"E Noyon";
      if(homePhoto) homePhoto.src=photo;
      if(profileName) profileName.innerText=name||"E Noyon";
      if(profilePhoto) profilePhoto.src=photo;
      if(profileUsername) profileUsername.innerText=username;
      if(profileId) profileId.innerText="ID: "+(u.id||"123456");
    }
  }catch(e){console.log("TG Error",e)}
}

// Links
document.getElementById("vpnBtn").onclick=()=>window.open("https://play.google.com/store/apps/details?id=free.vpnaustralia.unlimited.tunnel.proxy.secure.hotspot","_blank");
document.getElementById("channelBtn").onclick=()=>window.open("https://t.me/SmartWorkCommunity","_blank");
document.getElementById("adminBtn").onclick=()=>window.open("https://t.me/noyonfb1020","_blank");

console.log("Auto Taka Machine Loaded");
