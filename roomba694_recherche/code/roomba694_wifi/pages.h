// pages.h — pages HTML du firmware roomba694_wifi (tableau de bord, /wifi, /update), incluses par web.ino.
// Fichier .h séparé exprès : l'outil Arduino cherche des prototypes de fonctions dans les fichiers .ino et se trompe
// sur le JavaScript des pages (« function ... » pris pour du C++). Les .h ne sont pas analysés.
#pragma once
#include <Arduino.h>

// ---------- Page principale ----------
static const char PAGE_INDEX[] PROGMEM = R"=====(<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Roomba 694</title>
<style>
:root{--bg:#0f1115;--card:#1a1e26;--line:#2a3040;--txt:#e8eaf0;--mut:#9aa3b5;--ok:#3ddc84;--warn:#ffb300;--bad:#ff5252;--acc:#4f8cff}
*{box-sizing:border-box}
body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;margin:0;background:var(--bg);color:var(--txt);-webkit-tap-highlight-color:transparent}
header{position:sticky;top:0;background:#0f1115e6;backdrop-filter:blur(6px);padding:10px 14px;border-bottom:1px solid var(--line);z-index:2}
h1{font-size:1.15em;margin:0;display:flex;justify-content:space-between;align-items:baseline}
h1 small{color:var(--mut);font-weight:400;font-size:.75em}
#st{margin-top:6px;font-size:.92em;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.dot{width:10px;height:10px;border-radius:50%;background:var(--mut);flex:none}
.dot.ok{background:var(--ok)}.dot.bad{background:var(--bad)}.dot.warn{background:var(--warn)}
#net{color:var(--mut);font-size:.85em;margin-top:3px}
main{padding:10px 12px 30px;max-width:560px;margin:0 auto}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px;margin:10px 0}
.card h2{font-size:.8em;text-transform:uppercase;letter-spacing:.08em;color:var(--mut);margin:0 0 10px}
.row{display:flex;gap:8px;flex-wrap:wrap}
button{font:inherit;font-size:.95em;padding:11px 10px;border:0;border-radius:11px;background:#2a3040;color:var(--txt);flex:1 1 auto;min-width:0;touch-action:manipulation;user-select:none;-webkit-user-select:none}
button:active{filter:brightness(1.35)}
button.pri{background:var(--acc)}
button.on{outline:2px solid var(--ok)}
button.danger{background:#5a1f1f}
.pad{display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;max-width:270px;margin:0 auto}
.pad button{aspect-ratio:1;font-size:1.6em;padding:0;touch-action:none;-webkit-touch-callout:none}
.pad .stop{background:#b00020;font-size:1em;font-weight:700}
.pad .go{background:#1f3b6e}
.speed{display:flex;align-items:center;gap:10px;margin-top:12px;font-size:.9em;color:var(--mut)}
.speed input{flex:1}
.kv{display:grid;grid-template-columns:1fr 1fr;gap:6px 12px;font-size:.92em}
.kv div{color:var(--mut)}
.kv div b{display:block;font-size:1.25em;font-weight:600;color:var(--txt)}
.bat{height:10px;background:#2a3040;border-radius:5px;overflow:hidden;margin:8px 0 4px}
.bat i{display:block;height:100%;background:var(--ok);width:0}
svg{display:block;margin:0 auto;max-width:100%}
#log{font:12px/1.4 ui-monospace,Menlo,Consolas,monospace;background:#0b0d12;border-radius:10px;padding:8px;height:170px;overflow-y:auto;white-space:pre-wrap;word-break:break-word;color:#c9d1e0}
.send{display:flex;gap:8px;margin-top:8px}
.send input{flex:1;font:inherit;padding:10px;border-radius:10px;border:1px solid var(--line);background:#0b0d12;color:var(--txt)}
.hint{color:var(--mut);font-size:.82em;margin:6px 0 0}
a{color:#8cb4ff}
footer{text-align:center;color:var(--mut);font-size:.85em;padding:10px}
.row label{display:flex;align-items:center;gap:5px;flex:1 1 auto;color:var(--mut);font-size:.9em;white-space:nowrap}
select{font:inherit;font-size:.9em;background:#0b0d12;color:var(--txt);border:1px solid var(--line);border-radius:8px;padding:4px 6px}
canvas{display:block;margin:10px auto 0;width:100%;max-width:320px;touch-action:manipulation}
</style></head><body>
<header>
<h1>Roomba 694 <small id="ver">…</small></h1>
<div id="st"><span class="dot" id="dot"></span><span id="sttxt">connexion à la carte…</span></div>
<div id="net"></div>
</header>
<main>

<div class="card"><h2>Robot</h2>
<div class="row">
<button onclick="cmd('w')">Réveil BRC (w)</button>
<button class="pri" onclick="cmd('s')">Passive (s)</button>
<button onclick="cmd('f')">Safe (f)</button>
<button onclick="cmd('x')">Stop OI (x)</button>
</div>
<p class="hint">Robot endormi : appuyez sur CLEAN sur le robot (ou Réveil), puis Passive. Le mode Safe est nécessaire pour les notes, les LEDs et les roues. En fin de session : Stop OI.</p>
</div>

<div class="card"><h2>Pilotage <span id="drv" style="color:var(--bad)"></span></h2>
<div class="pad">
<span></span><button class="go" data-k="8">&#9650;</button><span></span>
<button class="go" data-k="4">&#8634;</button><button class="stop" onclick="cmd(' ')">STOP</button><button class="go" data-k="6">&#8635;</button>
<span></span><button class="go" data-k="2">&#9660;</button><span></span>
</div>
<div class="speed">vitesse <input type="range" id="spd" min="50" max="150" step="10" value="150"> <span id="spdv">150 mm/s</span></div>
<p class="hint">Maintenez une flèche pour rouler : les roues s'arrêtent dès que vous relâchez (et d'elles-mêmes 1,5 s après le dernier ordre). Mode Safe requis.</p>
</div>

<div class="card"><h2>Position <span id="pzst" style="text-transform:none;letter-spacing:0;color:var(--warn)"></span></h2>
<canvas id="pc" width="320" height="320" style="border-radius:10px"></canvas>
<div class="kv" style="margin-top:8px">
<div>Vers l'avant (x)<b id="px">–</b></div><div>Vers la gauche (y)<b id="py">–</b></div>
<div>Cap<b id="pcap">–</b></div><div>Chemin parcouru<b id="pdist">–</b></div>
<div style="grid-column:1/3">Écart au point de départ<b id="pecart">–</b></div>
</div>
<div class="row" style="margin-top:8px"><button onclick="poseZero()">Remettre la position à zéro (0)</button></div>
<p class="hint">Position calculée par le cerveau avec les compteurs des roues et le gyroscope. Le point blanc est le départ, le haut du dessin est l'avant du robot au départ, un carreau = <span id="pgrid">25 cm</span>. Essai : faire un carré et revenir au départ ; l'écart doit rester petit.</p>
</div>

<div class="card"><h2>Batterie et mode</h2>
<div class="kv">
<div>Charge<b id="pct">–</b></div><div>Mode OI<b id="mode">–</b></div>
<div>Tension<b id="v">–</b></div><div>Courant<b id="i">–</b></div>
<div>Température<b id="t">–</b></div><div>État<b id="chg">–</b></div>
</div>
<div class="bat"><i id="batbar"></i></div>
<div class="hint" id="mah"></div>
</div>

<div class="card"><h2>Capteurs</h2>
<svg viewBox="0 0 240 240" width="240" height="240">
 <circle cx="120" cy="120" r="92" fill="#232a38" stroke="#3a4255" stroke-width="2"/>
 <path id="bl" d="M120 28 A92 92 0 0 0 30 100" fill="none" stroke="#3a4255" stroke-width="12" stroke-linecap="round"/>
 <path id="br" d="M120 28 A92 92 0 0 1 210 100" fill="none" stroke="#3a4255" stroke-width="12" stroke-linecap="round"/>
 <g id="lb" fill="#3a4255">
  <circle cx="52" cy="78" r="7"/><circle cx="78" cy="52" r="7"/><circle cx="106" cy="40" r="7"/>
  <circle cx="134" cy="40" r="7"/><circle cx="162" cy="52" r="7"/><circle cx="188" cy="78" r="7"/>
 </g>
 <g id="cl" fill="#3a4255">
  <rect x="38" y="112" width="12" height="12" rx="3"/><rect x="82" y="60" width="12" height="12" rx="3"/>
  <rect x="146" y="60" width="12" height="12" rx="3"/><rect x="190" y="112" width="12" height="12" rx="3"/>
 </g>
 <rect id="wl" x="66" y="104" width="12" height="34" rx="4" fill="#3a4255"/>
 <rect id="wr" x="162" y="104" width="12" height="34" rx="4" fill="#3a4255"/>
 <text x="120" y="126" text-anchor="middle" fill="#9aa3b5" font-size="11">avant &#8593;</text>
 <text x="120" y="225" text-anchor="middle" fill="#6b7386" font-size="9.5">arcs : pare-chocs · points : light bumper</text>
 <text x="120" y="237" text-anchor="middle" fill="#6b7386" font-size="9.5">carrés : capteurs de vide · barres : roues levées</text>
</svg>
<div class="kv" style="margin-top:8px">
<div>Encodeurs G / D<b id="enc">–</b></div><div>Boutons<b id="btn">–</b></div>
<div>Vide (G, AvG, AvD, D)<b id="cliff" style="font-size:.95em">–</b></div><div>Light bumper (6)<b id="light" style="font-size:.95em">–</b></div>
</div>
</div>

<div class="card"><h2>Radar à ultrasons <span id="rdst" style="text-transform:none;letter-spacing:0"></span></h2>
<div class="row">
<button id="rm0" onclick="radar('mode=off')">Arrêt</button>
<button id="rm1" onclick="radar('mode=fixe&angle=0')">Fixe devant</button>
<button id="rm2" onclick="radar('mode=balayage')">Balayage</button>
</div>
<canvas id="rc" width="320" height="190"></canvas>
<div class="kv" style="margin-top:8px">
<div>Devant<b id="rfront">–</b></div><div>Capteur vers<b id="rservo">–</b></div>
</div>
<div class="speed">seuil d'arrêt <input type="range" id="rseuil" min="10" max="100" step="5" value="30"> <span id="rseuilv">30 cm</span></div>
<div class="row" style="margin-top:8px">
<label><input type="checkbox" id="rsec" onchange="radar('securite='+(this.checked?1:0))">arrêt auto</label>
<label><input type="checkbox" id="rauto" onchange="radar('auto='+(this.checked?1:0))">devant en marche avant</label>
<label><input type="checkbox" id="rinv" onchange="radar('inv='+(this.checked?1:0))">servo inversé</label>
</div>
<div class="row" style="margin-top:8px">
<label>pas <select id="rpas" onchange="radar('pas='+this.value)"><option>5</option><option>10</option><option>15</option><option>20</option></select>°</label>
<label>±<select id="ramp" onchange="radar('amplitude='+this.value)"><option>20</option><option>30</option><option>45</option><option>60</option><option>80</option></select>°</label>
<label>portée <select id="rport" onchange="if(rd)drawRadar(rd)"><option>100</option><option selected>200</option><option>400</option></select> cm</label>
<button style="flex:0 0 auto" onclick="radar('effacer=1')">Effacer</button>
</div>
<div class="row" style="margin-top:8px">
<label>butée du servo ±<select id="rmax" onchange="radar('butee='+this.value)"><option>15</option><option>20</option><option>30</option><option>45</option><option>60</option><option>80</option></select>°</label>
</div>
<p class="hint">HC-SR04 sur servo SG90 : 0° = devant, positif = gauche. Touchez le dessin pour orienter le capteur (mode fixe). Les points pâlissent avec l'âge, l'arc rouge pointillé est le seuil d'arrêt, le trait bleu la direction du capteur, les deux traits orange la butée du servo.</p>
</div>

<div class="card"><h2>Gyroscope</h2>
<div style="display:flex;align-items:center;gap:14px">
<svg viewBox="0 0 120 120" width="120" height="120" style="margin:0;flex:none">
 <circle cx="60" cy="60" r="54" fill="#232a38" stroke="#3a4255" stroke-width="2"/>
 <text x="60" y="16" text-anchor="middle" fill="#9aa3b5" font-size="10">0°</text>
 <g id="needle" transform="rotate(0 60 60)"><polygon points="60,14 54,60 66,60" fill="#4f8cff"/><polygon points="60,106 54,60 66,60" fill="#3a4255"/></g>
 <circle cx="60" cy="60" r="4" fill="#e8eaf0"/>
</svg>
<div class="kv" style="flex:1">
<div>Cap<b id="yaw">–</b></div><div>Rotation<b id="rate">–</b></div>
<div style="grid-column:1/3"><button onclick="cmd('z')" style="width:100%">Remettre le cap à zéro (z)</button></div>
</div></div>
<p class="hint" id="imuhint"></p>
</div>

<div class="card"><h2>Actions</h2>
<div class="row">
<button onclick="cmd('m')">3 notes (m)</button><button onclick="cmd('l')">LEDs (l)</button>
<button id="ba" onclick="cmd('a')">Anti-veille (a)</button><button id="bj" onclick="cmd('j')">CSV (j)</button>
</div>
<div class="row" style="margin-top:8px">
<button onclick="cmd('e')">Capteurs (e)</button><button onclick="cmd('k')">Encodeurs (k)</button><button onclick="cmd('b')">Batterie (b)</button><button onclick="cmd('i')">Infos (i)</button>
</div>
<div class="row" style="margin-top:8px">
<button class="danger" onclick="ask('c','Lancer un nettoyage ? Le robot part tout seul.')">Clean (c)</button>
<button class="danger" onclick="ask('h','Envoyer le robot à sa base ?')">Base (h)</button>
<button class="danger" onclick="ask('o','Éteindre le robot ?')">Éteindre (o)</button>
</div>
</div>

<div class="card"><h2>Console</h2>
<div id="log"></div>
<div class="send"><input id="key" placeholder="touche (ex. b, k, ?)" maxlength="1" autocomplete="off"><button class="pri" style="flex:0 0 auto" onclick="sendKey()">Envoyer</button></div>
</div>

<footer><a href="/wifi">Réseau Wi-Fi de la maison</a> · <a href="/update">Mise à jour du firmware</a><br><span id="up"></span></footer>
</main>
<script>
const $=id=>document.getElementById(id);
async function cmd(c){try{await fetch('/api/cmd?c='+encodeURIComponent(c));}catch(e){}}
function ask(c,q){if(confirm(q))cmd(c);}
function sendKey(){const k=$('key').value;if(k){cmd(k[0]);$('key').value='';}}
$('key').addEventListener('keydown',e=>{if(e.key==='Enter')sendKey();});
let hold=null;
function holdStart(k,e){e.preventDefault();if(hold)clearInterval(hold);cmd(k);hold=setInterval(()=>cmd(k),400);}
function holdEnd(){if(hold){clearInterval(hold);hold=null;cmd(' ');}}
document.querySelectorAll('.pad button[data-k]').forEach(b=>{
 b.addEventListener('pointerdown',e=>holdStart(b.dataset.k,e));
 ['pointerup','pointercancel','pointerleave'].forEach(ev=>b.addEventListener(ev,holdEnd));
 b.addEventListener('contextmenu',e=>e.preventDefault());
});
window.addEventListener('pointerup',holdEnd);
window.addEventListener('blur',holdEnd);
$('spd').addEventListener('input',()=>{$('spdv').textContent=$('spd').value+' mm/s';});
$('spd').addEventListener('change',()=>{fetch('/api/speed?v='+$('spd').value).catch(()=>{});});
const MODES={1:'Off',2:'Passive',3:'Safe',4:'Full'};
const CHG={0:'pas en charge',1:'reconditionnement',2:'en charge (pleine puissance)',3:"charge d'entretien",4:'attente',5:'défaut'};
function col(on,c){return on?c:'#3a4255';}
async function refresh(){
 try{
  const s=await (await fetch('/api/state')).json(); const b=s.robot;
  $('ver').textContent=s.ver+' · '+Math.round(s.ms/1000)+' s';
  $('dot').className='dot '+(b.ok?'ok':'bad');
  $('sttxt').textContent=b.ok?('robot joignable · '+(MODES[b.mode]||('mode brut '+b.mode))+(s.driving?' · ROUES EN MOUVEMENT':'')):'robot sans réponse : CLEAN (ou Réveil) puis Passive';
  let net='réseau '+s.ap.ssid+' '+s.ap.ip+' ('+s.ap.clients+' appareil'+(s.ap.clients>1?'s':'')+')';
  if(s.sta.on)net+=' · maison '+s.sta.saved+' : '+s.sta.ip;
  else if(s.sta.saved)net+=' · maison '+s.sta.saved+' : '+(s.sta.err||'connexion…');
  else net+=' · maison : non configuré';
  $('net').textContent=net;
  $('drv').textContent=s.driving?'● en mouvement':'';
  if(document.activeElement!==$('spd')){$('spd').value=s.speed;$('spdv').textContent=s.speed+' mm/s';}
  const pct=b.qmax?Math.round(100*b.q/b.qmax):0;
  $('pct').textContent=b.ok?pct+' %':'–'; $('batbar').style.width=(b.ok?pct:0)+'%';
  $('batbar').style.background=pct<20?'var(--bad)':pct<40?'var(--warn)':'var(--ok)';
  $('mode').textContent=b.ok?(MODES[b.mode]||'?')+' (brut '+b.mode+')':'–';
  $('v').textContent=b.ok?(b.v/1000).toFixed(2)+' V':'–';
  $('i').textContent=b.ok?b.i+' mA':'–';
  $('t').textContent=b.ok?b.t+' °C':'–';
  $('chg').textContent=b.ok?(CHG[b.chg]||b.chg):'–';
  $('mah').textContent=b.ok?b.q+' / '+b.qmax+' mAh · dernière lecture il y a '+(b.age/1000).toFixed(1)+' s':'aucune lecture récente';
  $('bl').setAttribute('stroke',col(b.ok&&b.bump[0],'#ff5252'));
  $('br').setAttribute('stroke',col(b.ok&&b.bump[1],'#ff5252'));
  $('wl').setAttribute('fill',col(b.ok&&b.drop[0],'#ff5252'));
  $('wr').setAttribute('fill',col(b.ok&&b.drop[1],'#ff5252'));
  const lbs=$('lb').children;for(let k=0;k<6;k++){const v=b.ok?b.light[k]:0;lbs[k].setAttribute('fill',v>0?'rgba(255,179,0,'+Math.min(1,0.25+v/1500)+')':'#3a4255');}
  const cls=$('cl').children;for(let k=0;k<4;k++){cls[k].setAttribute('fill',b.ok?(b.cliff[k]<100?'#ff5252':'#3ddc84'):'#3a4255');}
  $('enc').textContent=b.ok?b.enc[0]+' / '+b.enc[1]:'–';
  $('btn').textContent=b.ok?(b.btn?('bits '+b.btn):'aucun'):'–';
  $('cliff').textContent=b.ok?b.cliff.join(', '):'–';
  $('light').textContent=b.ok?b.light.join(', '):'–';
  if(s.imu.ok){$('yaw').textContent=s.imu.yaw.toFixed(1)+'°';$('rate').textContent=s.imu.rate.toFixed(1)+' °/s';
   $('needle').setAttribute('transform','rotate('+(-s.imu.yaw)+' 60 60)');
   $('imuhint').textContent=s.imu.cal?'calibration en cours, ne bougez pas le robot…':'cap positif = rotation vers la gauche (anti-horaire), comme l\'OI ; z remet à zéro, robot immobile';}
  else{$('yaw').textContent='–';$('rate').textContent='–';$('imuhint').textContent='MPU-6050 non détecté';}
  $('ba').className=s.keep?'on':'';$('bj').className=s.csv?'on':'';
  $('up').textContent='capteurs lus par le '+s.lecture+' · '+s.host+'.local · dernier redémarrage de la carte : '+s.rst+(s.robot_redem?' · robot vu redémarrer '+s.robot_redem+' fois':'');
  if(s.pose){ps=s.pose;ps.ok=b.ok;syncPose();}
 }catch(e){$('dot').className='dot warn';$('sttxt').textContent='carte injoignable…';}
}
let ps=null,pz={gen:0,pts:[]},pbusy=false;
async function syncPose(){
 if((ps.gen!==pz.gen||ps.n!==pz.pts.length)&&!pbusy){pbusy=true;
  try{const r=await (await fetch('/api/pose?gen='+pz.gen+'&from='+pz.pts.length)).json();
   if(r.from===0)pz.pts=r.points;else if(r.from===pz.pts.length)for(const q of r.points)pz.pts.push(q);
   pz.gen=r.gen;}catch(e){}
  pbusy=false;}
 drawPose();
}
async function poseZero(){try{await fetch('/api/pose?zero=1');}catch(e){}pz={gen:0,pts:[]};}
function drawPose(){
 const p=ps;if(!p)return;
 const cap=((p.cap+180)%360+360)%360-180;
 $('px').textContent=(p.x/10).toFixed(0)+' cm';$('py').textContent=(p.y/10).toFixed(0)+' cm';
 $('pcap').textContent=cap.toFixed(0)+'°';$('pdist').textContent=(p.dist/1000).toFixed(2)+' m';
 $('pecart').textContent=(Math.hypot(p.x,p.y)/10).toFixed(0)+' cm';
 $('pzst').textContent=p.leve?'· robot soulevé : position perdue':p.leves?'· soulevé '+p.leves+' fois : à remettre à zéro':p.sauts?'· '+p.sauts+' déplacement(s) non compté(s)':!p.gyro?'· sans gyroscope':'';
 const c=$('pc'),x=c.getContext('2d'),W=c.width,H=c.height;
 let x0=Math.min(0,p.x),x1=Math.max(0,p.x),y0=Math.min(0,p.y),y1=Math.max(0,p.y);
 for(const q of pz.pts){if(q[0]<x0)x0=q[0];if(q[0]>x1)x1=q[0];if(q[1]<y0)y0=q[1];if(q[1]>y1)y1=q[1];}
 const span=Math.max(2000,x1-x0+700,y1-y0+700),s=W/span,mx=(x0+x1)/2,my=(y0+y1)/2;
 const X=wy=>W/2-(wy-my)*s,Y=wx=>H/2-(wx-mx)*s;
 let g=10000;for(const k of[250,500,1000,2000,5000])if(k*s>=26){g=k;break;}
 $('pgrid').textContent=g<1000?(g/10)+' cm':(g/1000)+' m';
 x.clearRect(0,0,W,H);x.fillStyle='#232a38';x.fillRect(0,0,W,H);
 x.lineWidth=1;
 for(let k=Math.ceil((mx-span/2)/g);k*g<=mx+span/2;k++){x.strokeStyle=k?'#2f3748':'#465069';x.beginPath();x.moveTo(0,Y(k*g));x.lineTo(W,Y(k*g));x.stroke();}
 for(let k=Math.ceil((my-span/2)/g);k*g<=my+span/2;k++){x.strokeStyle=k?'#2f3748':'#465069';x.beginPath();x.moveTo(X(k*g),0);x.lineTo(X(k*g),H);x.stroke();}
 x.strokeStyle='#4f8cff';x.lineWidth=2;x.lineJoin='round';x.beginPath();
 pz.pts.forEach((q,k)=>{if(k)x.lineTo(X(q[1]),Y(q[0]));else x.moveTo(X(q[1]),Y(q[0]));});
 if(pz.pts.length)x.lineTo(X(p.y),Y(p.x));x.stroke();
 x.fillStyle='#e8eaf0';x.beginPath();x.arc(X(0),Y(0),4,0,7);x.fill();
 const r=Math.max(5,170*s),t=p.cap*Math.PI/180,rx=X(p.y),ry=Y(p.x);
 x.strokeStyle=p.ok?'#3ddc84':'#9aa3b5';x.lineWidth=2;x.beginPath();x.arc(rx,ry,r,0,7);x.stroke();
 x.beginPath();x.moveTo(rx,ry);x.lineTo(rx-r*Math.sin(t),ry-r*Math.cos(t));x.stroke();
}
let seq=0;
async function pollLog(){
 try{const r=await (await fetch('/api/log?since='+seq)).json();
  if(r.lines.length){const L=$('log');const atEnd=L.scrollHeight-L.scrollTop-L.clientHeight<30;
   r.lines.forEach((l,k)=>{if(r.from+k<seq)return;const d=document.createElement('div');d.textContent=l;L.appendChild(d);});
   while(L.children.length>80)L.removeChild(L.firstChild);
   if(atEnd)L.scrollTop=L.scrollHeight;}
  seq=r.seq;
 }catch(e){}
}
let rd=null;
async function radar(q){try{drawRadar(await (await fetch('/api/radar?'+q)).json());}catch(e){}}
async function pollRadar(){try{drawRadar(await (await fetch('/api/radar')).json());}catch(e){}}
function drawRadar(r){
 rd=r;
 for(let k=0;k<3;k++)$('rm'+k).className=(r.mode===k?'on':'');
 $('rdst').textContent=r.absent?'· capteur sans réaction':(r.following?'· devant (marche avant)':'');
 const fresh=r.front_age<3000;
 $('rfront').textContent=(!fresh||r.front_cm<0)?'–':(r.front_cm>0?r.front_cm.toFixed(0)+' cm':'rien < 4 m');
 $('rfront').style.color=(fresh&&r.front_cm>0&&r.front_cm<r.seuil)?'var(--bad)':'';
 $('rservo').textContent=(r.servo>0?'+':'')+r.servo+'°';
 if(document.activeElement!==$('rseuil')){$('rseuil').value=r.seuil;$('rseuilv').textContent=r.seuil+' cm';}
 $('rsec').checked=r.securite;$('rauto').checked=r.auto;$('rinv').checked=r.inv;$('rpas').value=r.pas;$('ramp').value=r.amplitude;$('rmax').value=r.butee;
 const c=$('rc'),x=c.getContext('2d'),W=c.width,H=c.height,cx=W/2,cy=H-16,R=H-32,port=+$('rport').value;
 x.clearRect(0,0,W,H);
 x.fillStyle='#232a38';x.beginPath();x.moveTo(cx,cy);x.arc(cx,cy,R,Math.PI,2*Math.PI);x.closePath();x.fill();
 x.strokeStyle='#3a4255';x.lineWidth=1;
 for(let k=1;k<=4;k++){x.beginPath();x.arc(cx,cy,R*k/4,Math.PI,2*Math.PI);x.stroke();}
 for(const a of[-60,-30,0,30,60]){const t=a*Math.PI/180;x.beginPath();x.moveTo(cx,cy);x.lineTo(cx-R*Math.sin(t),cy-R*Math.cos(t));x.stroke();}
 x.fillStyle='#6b7386';x.font='10px system-ui';x.textAlign='left';
 for(let k=1;k<=4;k++)x.fillText(Math.round(port*k/4)+'',cx+3,cy-R*k/4+10);
 x.textAlign='center';x.fillText('gauche',28,cy+12);x.fillText('droite',W-28,cy+12);
 x.strokeStyle='rgba(255,82,82,.7)';x.setLineDash([4,3]);x.beginPath();x.arc(cx,cy,R*Math.min(1,r.seuil/port),Math.PI,2*Math.PI);x.stroke();x.setLineDash([]);
 if(r.butee<80){x.strokeStyle='rgba(255,179,0,.75)';for(const a of[-r.butee,r.butee]){const t=a*Math.PI/180;x.beginPath();x.moveTo(cx,cy);x.lineTo(cx-R*Math.sin(t),cy-R*Math.cos(t));x.stroke();}}
 if(r.mode){const t=r.servo*Math.PI/180;x.strokeStyle='rgba(79,140,255,.8)';x.lineWidth=2;x.beginPath();x.moveTo(cx,cy);x.lineTo(cx-R*Math.sin(t),cy-R*Math.cos(t));x.stroke();x.lineWidth=1;}
 for(const p of r.points){const a=p[0]*Math.PI/180,cm=p[1]/10,age=p[2],al=Math.max(.2,1-age/8000);
  if(cm<=0){x.fillStyle='rgba(154,163,181,'+al+')';x.beginPath();x.arc(cx-(R-3)*Math.sin(a),cy-(R-3)*Math.cos(a),2,0,7);x.fill();continue;}
  const d=Math.min(1,cm/port),px=cx-R*d*Math.sin(a),py=cy-R*d*Math.cos(a);
  x.fillStyle=cm<r.seuil?'rgba(255,82,82,'+al+')':'rgba(61,220,132,'+al+')';
  x.beginPath();x.arc(px,py,cm>port?3:5,0,7);x.fill();
  if(cm>port){x.strokeStyle='rgba(61,220,132,'+al+')';x.beginPath();x.arc(px,py,6,0,7);x.stroke();}}
 x.fillStyle='#e8eaf0';x.beginPath();x.arc(cx,cy,4,0,7);x.fill();
}
$('rseuil').addEventListener('input',()=>{$('rseuilv').textContent=$('rseuil').value+' cm';});
$('rseuil').addEventListener('change',()=>radar('seuil='+$('rseuil').value));
$('rc').addEventListener('click',e=>{const c=$('rc'),b=c.getBoundingClientRect(),sx=c.width/b.width,sy=c.height/b.height;
 const dx=(e.clientX-b.left)*sx-c.width/2,dy=(c.height-16)-(e.clientY-b.top)*sy;if(dy<5)return;
 const lim=(rd&&rd.butee)||80,a=Math.max(-lim,Math.min(lim,Math.round(Math.atan2(-dx,dy)*180/Math.PI)));radar('mode=fixe&angle='+a);});
let rt=0;setInterval(()=>{rt++;if((rd&&rd.mode)||rt%4===0)pollRadar();},500);pollRadar();
setInterval(refresh,600);refresh();setInterval(pollLog,1000);pollLog();
</script></body></html>
)=====";

// ---------- Page /wifi ----------
static const char PAGE_WIFI[] PROGMEM = R"=====(<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Wi-Fi · Roomba 694</title>
<style>
:root{--bg:#0f1115;--card:#1a1e26;--line:#2a3040;--txt:#e8eaf0;--mut:#9aa3b5;--ok:#3ddc84;--bad:#ff5252;--acc:#4f8cff}
*{box-sizing:border-box}
body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;margin:0;background:var(--bg);color:var(--txt)}
header{padding:12px 14px;border-bottom:1px solid var(--line)}h1{font-size:1.15em;margin:0}
main{padding:10px 12px 30px;max-width:560px;margin:0 auto}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px;margin:10px 0}
.card h2{font-size:.8em;text-transform:uppercase;letter-spacing:.08em;color:var(--mut);margin:0 0 10px}
button{font:inherit;font-size:.95em;padding:11px 12px;border:0;border-radius:11px;background:#2a3040;color:var(--txt);width:100%;margin:4px 0;text-align:left}
button.pri{background:var(--acc);text-align:center}button.danger{background:#5a1f1f;text-align:center}
button:disabled{opacity:.5}
label{display:block;color:var(--mut);font-size:.9em;margin-top:8px}
input{font:inherit;width:100%;padding:11px;border-radius:10px;border:1px solid var(--line);background:#0b0d12;color:var(--txt);margin-top:4px}
.pw{display:flex;gap:8px;align-items:center}.pw button{width:auto;flex:none;margin-top:4px}
.hint{color:var(--mut);font-size:.85em}.bad{color:var(--bad)}
ul.hint{padding-left:18px;margin:0}ul.hint li{margin:4px 0}
a{color:#8cb4ff}footer{text-align:center;padding:10px}
</style></head><body>
<header><h1>Réseau Wi-Fi de la maison</h1></header>
<main>
<div class="card"><h2>État</h2><div id="state">…</div></div>
<div class="card"><h2>Réseaux à portée</h2>
<button id="scan" class="pri" onclick="scan()">Chercher les réseaux</button>
<div id="list"></div>
<p class="hint">Touchez un réseau pour remplir son nom ci-dessous.</p>
</div>
<div class="card"><h2>Enregistrer</h2>
<form id="f" onsubmit="return save(event)">
<label>Nom du réseau (SSID)<input name="ssid" id="ssid" required autocomplete="off" autocapitalize="off"></label>
<label>Mot de passe<span class="pw"><input name="pass" id="pass" type="password" autocomplete="off"><button type="button" onclick="togglePw()">voir</button></span></label>
<button class="pri" type="submit" style="margin-top:12px">Enregistrer et connecter</button>
</form>
<div id="msg" class="hint"></div>
<button class="danger" style="margin-top:10px" onclick="forget()">Oublier le réseau enregistré</button>
</div>
<div class="card"><h2>Conseils</h2>
<ul class="hint">
<li>Restez connecté au réseau « Roomba694 » pendant l'opération, même si le téléphone signale « pas d'internet ».</li>
<li>La carte ne voit que les réseaux 2,4 GHz.</li>
<li>Le nom et le mot de passe restent dans la carte : ils ne sont ni affichés ni envoyés ailleurs.</li>
<li>Une fois connectée, la carte reste joignable sur 192.168.4.1 via « Roomba694 », et depuis le réseau de la maison à l'adresse indiquée dans l'état, ou sur http://roomba694.local.</li>
</ul></div>
<footer><a href="/">Retour au tableau de bord</a></footer>
</main>
<script>
const $=id=>document.getElementById(id);
async function refresh(){try{const s=await (await fetch('/api/state')).json();let t;
 if(!s.sta.saved)t='Aucun réseau enregistré.';
 else if(s.sta.on)t='« '+s.sta.saved+' » : connecté, adresse <b>'+s.sta.ip+'</b><br>Depuis le réseau de la maison : <a href="http://'+s.sta.ip+'/">http://'+s.sta.ip+'/</a> ou <a href="http://'+s.host+'.local/">http://'+s.host+'.local/</a>';
 else t='« '+s.sta.saved+' » : '+(s.sta.err?'<span class="bad">échec, '+s.sta.err+'</span> — nouvelle tentative automatique':'connexion en cours…');
 $('state').innerHTML=t;}catch(e){$('state').textContent='carte injoignable… (le téléphone est-il toujours sur le réseau Roomba694 ?)';}}
async function scan(){$('scan').disabled=true;$('list').textContent='recherche…';
 for(let k=0;k<12;k++){
  try{const r=await (await fetch('/api/scan')).json();
   if(r.status==='done'){
    if(!r.networks.length)$('list').textContent='aucun réseau trouvé';
    else{$('list').innerHTML='';for(const n of r.networks){const b=document.createElement('button');b.type='button';
     b.textContent=n.ssid+'   ('+n.rssi+' dBm'+(n.open?', ouvert':'')+')';b.onclick=()=>{$('ssid').value=n.ssid;$('pass').focus();};$('list').appendChild(b);}}
    break;}
  }catch(e){}
  await new Promise(r=>setTimeout(r,1000));}
 $('scan').disabled=false;}
async function save(e){e.preventDefault();$('msg').textContent='enregistrement…';
 try{const r=await fetch('/wifi',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:new URLSearchParams(new FormData($('f')))});
  const j=await r.json();
  $('msg').textContent=j.ok?'Enregistré. Connexion en cours : l\'état ci-dessus se met à jour tout seul (10 à 20 s).':('Erreur : '+j.msg);
  if(j.ok)$('pass').value='';}
 catch(e){$('msg').textContent='Pas de réponse de la carte : le téléphone a peut-être quitté le réseau Roomba694. Vérifiez l\'état ci-dessus.';}
 return false;}
async function forget(){if(!confirm('Oublier le réseau enregistré ?'))return;try{await fetch('/wifi/forget',{method:'POST'});}catch(e){}refresh();}
function togglePw(){const p=$('pass');p.type=p.type==='password'?'text':'password';}
setInterval(refresh,1500);refresh();
</script></body></html>
)=====";

// ---------- Page /update ----------
static const char PAGE_UPDATE[] PROGMEM = R"=====(<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mise à jour · Roomba 694</title>
<style>body{font-family:system-ui,sans-serif;margin:16px;background:#0f1115;color:#e8eaf0;max-width:560px}input,button{font-size:1em;padding:10px;margin:8px 0;display:block;border-radius:10px;border:1px solid #2a3040;background:#1a1e26;color:#e8eaf0}button{background:#4f8cff;border:0}a{color:#8cb4ff}code{color:#ffb300}p{color:#9aa3b5}</style>
</head><body><h1>Mise à jour du firmware</h1>
<p>Fichier attendu : le <code>.bin</code> produit par <code>arduino-cli compile --export-binaries</code>
(<code>build/esp32.esp32.esp32/roomba694_wifi.ino.bin</code>). Les roues sont arrêtées au début de l'envoi ; la carte redémarre à la fin (30 s environ).</p>
<p>Sans mot de passe : l'envoi est accepté depuis cette page ou depuis un appareil du réseau, à l'adresse du robot.</p>
<form method="post" action="/update" enctype="multipart/form-data">
<input type="file" name="firmware" accept=".bin" required>
<button>Envoyer et redémarrer</button></form>
<p><a href="/">Retour</a></p></body></html>
)=====";
