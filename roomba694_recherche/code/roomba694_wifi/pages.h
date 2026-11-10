// pages.h — pages HTML du firmware roomba694_wifi (tableau de bord, /wifi, /update), incluses par web.ino.
// Fichier .h séparé exprès : l'outil Arduino cherche des prototypes de fonctions dans les fichiers .ino et se trompe
// sur le JavaScript des pages (« function ... » pris pour du C++). Les .h ne sont pas analysés.
#pragma once
#include <Arduino.h>

// ---------- Page principale ----------
static const char PAGE_INDEX[] PROGMEM = R"=====(<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<title>Roomba 694</title>
<style>
:root{color-scheme:light dark;
--plane:#f4f4f1;--surface:#fcfcfb;--surface2:#eeede8;--ink:#0b0b0b;--ink2:#52514e;--mut:#898781;
--line:#e1e0d9;--axis:#c3c2b7;--ring:rgba(11,11,11,.10);
--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;
--good:#0ca30c;--warn:#fab219;--serious:#ec835a;--crit:#d03b3b;--accent:#2a78d6}
@media (prefers-color-scheme:dark){:root{
--plane:#0d0d0d;--surface:#1a1a19;--surface2:#272725;--ink:#f0efec;--ink2:#c3c2b7;--mut:#898781;
--line:#2c2c2a;--axis:#383835;--ring:rgba(255,255,255,.10);
--s1:#3987e5;--s2:#d95926;--s3:#199e70;--accent:#3987e5}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--plane);color:var(--ink);font:15px/1.4 system-ui,-apple-system,"Segoe UI",sans-serif;-webkit-tap-highlight-color:transparent}
header{position:sticky;top:0;z-index:5;background:var(--plane);border-bottom:1px solid var(--ring);padding:10px 14px;display:flex;align-items:center;justify-content:space-between;gap:10px}
header h1{font-size:1.05rem;font-weight:650;margin:0}
.pill{display:flex;align-items:center;gap:7px;font-size:.9rem;color:var(--ink2);min-width:0}
.pill span:last-child{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dot{width:9px;height:9px;border-radius:50%;background:var(--mut);flex:none}
.dot.ok{background:var(--good)}.dot.warn{background:var(--warn)}.dot.bad{background:var(--crit)}
main{max-width:1160px;margin:0 auto;padding:12px;display:grid;gap:12px;align-items:start;grid-template-columns:minmax(0,1fr);grid-template-areas:"map" "drive" "info" "more"}
#gmap{grid-area:map}#gdrive{grid-area:drive}#ginfo{grid-area:info}#gmore{grid-area:more}
.col{display:grid;gap:12px;align-content:start;min-width:0}
@media (min-width:900px){main{grid-template-columns:minmax(0,1.4fr) minmax(330px,1fr);grid-template-areas:"map drive" "map more" "info more"}}
.card{background:var(--surface);border:1px solid var(--ring);border-radius:16px;padding:14px;min-width:0}
h2,.lab{font-size:.8rem;font-weight:500;color:var(--mut);margin:0}
button{font:inherit;color:var(--ink);background:var(--surface2);border:0;border-radius:12px;min-height:44px;padding:0 14px;white-space:nowrap;touch-action:manipulation;user-select:none;-webkit-user-select:none;cursor:pointer}
button:active{filter:brightness(.9)}
button.pri{background:var(--accent);color:#fff;font-weight:600}
button.ghost{background:transparent;border:1px solid var(--ring)}
button.danger{color:var(--crit)}
button[disabled]{opacity:.45}
button.on{box-shadow:inset 0 0 0 2px var(--accent)}
.row{display:flex;gap:8px;flex-wrap:wrap}.row>button{flex:1 1 auto}
.seg{display:flex;background:var(--surface2);border-radius:12px;padding:3px;gap:2px}
.seg button{flex:1;min-height:36px;border-radius:9px;background:transparent;padding:0 10px;font-size:.9rem;color:var(--ink2)}
.seg button.on{background:var(--surface);color:var(--ink);font-weight:600;box-shadow:0 0 0 1px var(--ring)}
.maphead{display:flex;justify-content:space-between;align-items:center;gap:10px}
.maphead .ctl{display:flex;gap:6px;align-items:center;flex:none}
.big{display:flex;align-items:baseline;gap:4px 10px;flex-wrap:wrap;margin:-4px 0 10px}
#map{display:block;width:100%;height:clamp(230px,calc(100dvh - 548px),520px);border-radius:10px;touch-action:pan-y}
@media (min-width:900px){#map{height:clamp(380px,66vh,700px)}}
.chip{min-height:38px;border-radius:12px;font-size:.9rem;padding:0 12px;color:var(--ink2)}.chip.on{color:var(--ink);font-weight:600;box-shadow:inset 0 0 0 2px var(--accent)}
.legend{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:.8rem;color:var(--ink2);margin:8px 0 0}
.legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:-1px}
.legend i.ln{width:14px;height:3px;border-radius:2px;vertical-align:3px}
.legend i.rg{background:transparent;box-shadow:inset 0 0 0 2px var(--s3)}
.hint{font-size:.82rem;color:var(--mut);margin:8px 0 0}
.num{font-size:3rem;line-height:1;font-weight:650;white-space:nowrap}
.sub{font-size:.85rem;color:var(--ink2)}
.tiles{display:grid;grid-template-columns:1fr 1fr;gap:10px 12px;margin-bottom:12px}
@media (min-width:520px){.tiles{grid-template-columns:repeat(4,minmax(0,1fr))}}
.val{font-size:1.2rem;font-weight:600;white-space:nowrap}
.alerts{display:grid;gap:6px}.alerts:not(:empty){margin-top:10px}
.al{display:flex;align-items:center;gap:8px;font-size:.9rem}
.ico{flex:none;width:18px;height:18px;border-radius:50%;color:#fff;font-size:.75rem;font-weight:700;display:grid;place-items:center;background:var(--crit)}
.ico.w{background:var(--warn);color:#0b0b0b}
.state{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:12px}
.pad{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;max-width:236px;margin:0 auto}
.pad button{aspect-ratio:1;min-height:0;padding:0;border-radius:18px;touch-action:none;-webkit-touch-callout:none;display:grid;place-items:center}
.pad svg{width:42%;height:42%;fill:none;stroke:currentColor;stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round}
.pad .stop{background:var(--crit);color:#fff;font-weight:700;letter-spacing:.04em}
.pad.lock button:not(.stop){opacity:.4}
.speed{display:flex;align-items:center;gap:10px;margin-top:12px;font-size:.88rem;color:var(--ink2)}
.speed input{flex:1;accent-color:var(--accent);min-width:0}
details.card{padding:0}
details.card>summary{list-style:none;cursor:pointer;padding:14px;display:flex;justify-content:space-between;align-items:center;gap:10px;font-weight:600}
details.card>summary::-webkit-details-marker{display:none}
details.card>summary small{font-weight:400;color:var(--ink2);font-size:.85rem;text-align:right}
details.card>div{padding:0 14px 14px}
.kv{display:grid;grid-template-columns:1fr 1fr;gap:10px 12px}
.meter{height:8px;border-radius:4px;background:color-mix(in srgb,var(--fill,var(--accent)) 22%,var(--surface));overflow:hidden;margin:10px 0 12px}
.meter i{display:block;height:100%;width:0;border-radius:4px;background:var(--fill,var(--accent))}
#rc{display:block;width:100%;max-width:340px;margin:10px auto 0;touch-action:manipulation}
.opts{display:flex;flex-wrap:wrap;gap:8px 14px;margin-top:10px;font-size:.88rem;color:var(--ink2)}
.opts label{display:flex;align-items:center;gap:6px;white-space:nowrap}
select,input[type=text]{font:inherit;color:var(--ink);background:var(--surface2);border:1px solid var(--ring);border-radius:9px;padding:6px 8px}
input[type=checkbox]{accent-color:var(--accent);width:18px;height:18px}
#log{font:12px/1.45 ui-monospace,Menlo,Consolas,monospace;background:var(--surface2);border-radius:10px;padding:8px;height:190px;overflow-y:auto;white-space:pre-wrap;word-break:break-word;color:var(--ink2)}
.send{display:flex;gap:8px;margin-top:8px}.send input{flex:1;min-width:0;min-height:44px}
svg.bot{display:block;margin:0 auto;max-width:210px}
svg.bot .b{fill:var(--surface2);stroke:var(--axis);stroke-width:2}
svg.bot .o{fill:var(--axis)}svg.bot .o.hit{fill:var(--crit)}svg.bot .o.seen{fill:var(--warn)}svg.bot .o.fine{fill:var(--good)}
svg.bot .a{fill:none;stroke:var(--axis);stroke-width:10;stroke-linecap:round}svg.bot .a.hit{stroke:var(--crit)}
svg.bot text{fill:var(--mut);font-size:10px}
footer{text-align:center;color:var(--mut);font-size:.82rem;padding:6px 12px 28px}
a{color:var(--accent)}
</style></head><body>
<header><h1>Roomba 694</h1><div class="pill"><span class="dot" id="dot"></span><span id="top">connexion…</span></div></header>
<main>

<section class="card" id="gmap">
<div class="maphead">
<div class="lab">Distance mesurée</div>
<div class="ctl"><div class="seg"><button id="vw0" class="on" onclick="setView(0)">Dessus</button><button id="vw1" onclick="setView(1)">3D</button></div><button class="chip" id="fit" onclick="toggleFit()">Suivre</button></div>
</div>
<div class="big"><span class="num" id="dist">–</span><span class="sub" id="distsub">capteur de distance à l'arrêt</span></div>
<canvas id="map"></canvas>
<div class="legend"><span><i class="ln" style="background:var(--s1)"></i>Tracé</span><span><i style="background:var(--s2)"></i>Obstacles vus</span><span><i class="rg"></i>Robot</span><span id="scale"></span></div>
<div class="alerts" id="alerts"></div>
</section>

<section class="card" id="ginfo">
<div class="tiles">
<div><div class="lab">Cap</div><div class="val" id="tcap">–</div></div>
<div><div class="lab">Avant ; gauche</div><div class="val" id="tpos">–</div></div>
<div><div class="lab">Chemin parcouru</div><div class="val" id="tdist">–</div></div>
<div><div class="lab">Écart au départ</div><div class="val" id="tecart">–</div></div>
</div>
<div class="lab" style="margin-bottom:6px">Capteur de distance</div>
<div class="seg"><button id="rm0" onclick="radar('mode=off')">Arrêté</button><button id="rm1" onclick="radar('mode=fixe&angle=0')">Devant</button><button id="rm2" onclick="radar('mode=balayage')">Balayage</button></div>
<div class="lab" style="margin:12px 0 6px">Carte</div>
<div class="row"><button id="btour" onclick="tour()">Tour sur place</button><button onclick="poseZero()">Nouveau départ</button><button onclick="carteClear()">Effacer les obstacles</button></div>
<p class="hint" id="maphint">Le haut de la carte est l'avant du robot au départ. « Tour sur place » : le robot tourne sur lui-même et dessine ce qui l'entoure.</p>
</section>

<section class="card" id="gdrive">
<div class="state"><div class="val" id="rstate">–</div><button class="pri" id="main" onclick="mainAction()">…</button></div>
<div class="pad lock" id="pad">
<span></span><button data-k="8" aria-label="Avancer"><svg viewBox="0 0 24 24"><path d="M12 19V5M5 12l7-7 7 7"/></svg></button><span></span>
<button data-k="4" aria-label="Tourner à gauche"><svg viewBox="0 0 24 24"><path d="M4 5v6h6M4.6 11A8 8 0 1 1 6 17.3"/></svg></button><button class="stop" onclick="cmd(' ')">STOP</button><button data-k="6" aria-label="Tourner à droite"><svg viewBox="0 0 24 24"><path d="M20 5v6h-6M19.4 11A8 8 0 1 0 18 17.3"/></svg></button>
<span></span><button data-k="2" aria-label="Reculer"><svg viewBox="0 0 24 24"><path d="M12 5v14M5 12l7 7 7-7"/></svg></button><span></span>
</div>
<div class="speed"><span>Vitesse</span><input type="range" id="spd" min="50" max="150" step="10" value="150"><span id="spdv">150 mm/s</span></div>
<p class="hint" id="drvhint">Maintenez une flèche pour rouler ; le robot s'arrête dès que vous relâchez.</p>
</section>

<div class="col" id="gmore">
<details class="card" id="dbat"><summary>Batterie<small id="sbat">–</small></summary><div>
<div class="meter" id="meter"><i id="batbar"></i></div>
<div class="kv">
<div><div class="lab">Tension</div><div class="val" id="v">–</div></div><div><div class="lab">Courant</div><div class="val" id="i">–</div></div>
<div><div class="lab">Température</div><div class="val" id="t">–</div></div><div><div class="lab">Réserve</div><div class="val" id="mah">–</div></div>
</div><p class="hint" id="bathint"></p></div></details>

<details class="card" id="dsens"><summary>Capteurs du robot<small id="ssens">–</small></summary><div>
<svg class="bot" viewBox="0 0 240 228" width="210">
<circle class="b" cx="120" cy="120" r="92"/>
<path class="a" id="bl" d="M120 28 A92 92 0 0 0 30 100"/><path class="a" id="br" d="M120 28 A92 92 0 0 1 210 100"/>
<g id="lb"><circle class="o" cx="52" cy="78" r="7"/><circle class="o" cx="78" cy="52" r="7"/><circle class="o" cx="106" cy="40" r="7"/><circle class="o" cx="134" cy="40" r="7"/><circle class="o" cx="162" cy="52" r="7"/><circle class="o" cx="188" cy="78" r="7"/></g>
<g id="cl"><rect class="o" x="38" y="112" width="12" height="12" rx="3"/><rect class="o" x="82" y="60" width="12" height="12" rx="3"/><rect class="o" x="146" y="60" width="12" height="12" rx="3"/><rect class="o" x="190" y="112" width="12" height="12" rx="3"/></g>
<rect class="o" id="wl" x="66" y="104" width="12" height="34" rx="4"/><rect class="o" id="wr" x="162" y="104" width="12" height="34" rx="4"/>
<text x="120" y="130" text-anchor="middle">avant ↑</text>
</svg>
<p class="hint">Arcs : pare-chocs. Points : capteurs optiques du pare-chocs. Carrés : capteurs de vide. Barres : roues.</p>
<div class="kv" style="margin-top:10px">
<div><div class="lab">Vide (G, avG, avD, D)</div><div class="sub" id="cliff">–</div></div><div><div class="lab">Capteurs optiques (6)</div><div class="sub" id="light">–</div></div>
<div><div class="lab">Compteurs des roues</div><div class="sub" id="enc">–</div></div><div><div class="lab">Moteurs des roues</div><div class="sub" id="cur">–</div></div>
</div></div></details>

<details class="card" id="drad"><summary>Capteur de distance : réglages<small id="srad">–</small></summary><div>
<canvas id="rc" width="340" height="200"></canvas>
<div class="speed"><span>Arrêt à</span><input type="range" id="rseuil" min="10" max="100" step="5" value="30"><span id="rseuilv">30 cm</span></div>
<div class="opts">
<label><input type="checkbox" id="rsec" onchange="radar('securite='+(this.checked?1:0))">arrêt automatique</label>
<label><input type="checkbox" id="rauto" onchange="radar('auto='+(this.checked?1:0))">regarde devant en avançant</label>
<label><input type="checkbox" id="rinv" onchange="radar('inv='+(this.checked?1:0))">servo inversé</label>
</div><div class="opts">
<label>pas <select id="rpas" onchange="radar('pas='+this.value)"><option>5</option><option>10</option><option>15</option><option>20</option></select>°</label>
<label>balayage ±<select id="ramp" onchange="radar('amplitude='+this.value)"><option>20</option><option>30</option><option>45</option><option>60</option><option>80</option></select>°</label>
<label>butée ±<select id="rmax" onchange="radar('butee='+this.value)"><option>15</option><option>20</option><option>30</option><option>45</option><option>60</option><option>80</option></select>°</label>
<label>portée <select id="rport" onchange="if(rd)drawRadar(rd)"><option>100</option><option selected>200</option><option>400</option></select> cm</label>
</div>
<p class="hint">Touchez le demi-cercle pour orienter le capteur. 0° = devant, positif = gauche. Le trait pointillé est la distance d'arrêt.</p>
</div></details>

<details class="card" id="dact"><summary>Autres commandes<small id="sgyro">–</small></summary><div>
<div class="row"><button onclick="cmd('w')">Réveil</button><button onclick="cmd('s')">Passive</button><button onclick="cmd('f')">Safe</button><button onclick="cmd('x')">Stop OI</button></div>
<div class="row" style="margin-top:8px"><button onclick="cmd('z')">Recaler le gyroscope</button><button onclick="cmd('m')">3 notes</button><button onclick="cmd('l')">Voyants</button></div>
<div class="row" style="margin-top:8px"><button id="ba" onclick="cmd('a')">Anti-veille</button><button id="bj" onclick="cmd('j')">Journal CSV</button><button onclick="cmd('i');openLog()">Infos</button></div>
<div class="row" style="margin-top:8px"><button class="danger" onclick="ask('c','Lancer un nettoyage ? Le robot part tout seul.')">Nettoyer</button><button class="danger" onclick="ask('h','Envoyer le robot à sa base ?')">Base</button><button class="danger" onclick="ask('o','Éteindre le robot ?')">Éteindre</button></div>
<p class="hint">Recaler le gyroscope : robot immobile, une seconde. Le cap affiché repart de zéro, la carte ne bouge pas.</p>
</div></details>

<details class="card" id="dlog"><summary>Console<small id="slog"></small></summary><div>
<div id="log"></div>
<div class="send"><input type="text" id="key" placeholder="touche (ex. b, k, ?)" maxlength="1" autocomplete="off"><button class="pri" onclick="sendKey()">Envoyer</button></div>
</div></details>

</div></main>
<footer><a href="/wifi">Réseau Wi-Fi</a> · <a href="/update">Mise à jour</a><br><span id="foot"></span></footer>
<script>
const $=id=>document.getElementById(id),wait=ms=>new Promise(r=>setTimeout(r,ms));
const RAD=Math.PI/180;
let C={};
function loadColors(){const g=getComputedStyle(document.documentElement);for(const k of['plane','surface','surface2','ink','ink2','mut','line','axis','s1','s2','s3','good','warn','crit','accent'])C[k]=g.getPropertyValue('--'+k).trim();}
loadColors();
async function cmd(c){try{await fetch('/api/cmd?c='+encodeURIComponent(c));}catch(e){}}
function ask(c,q){if(confirm(q))cmd(c);}
function sendKey(){const k=$('key').value;if(k){cmd(k[0]);$('key').value='';}}
$('key').addEventListener('keydown',e=>{if(e.key==='Enter')sendKey();});
function openLog(){$('dlog').open=true;}

// ---- État général ----
let S=null,busy=false;
const canDrive=()=>!!(S&&S.robot.ok&&S.robot.mode===3);
function nudge(){const m=$('main');m.animate([{transform:'scale(1)'},{transform:'scale(1.06)'},{transform:'scale(1)'}],{duration:350});}
async function mainAction(){
 if(busy||!S)return;const b=S.robot;
 if(b.ok&&b.mode===3&&!confirm('Terminer la session ? Les roues sont arrêtées et le robot reprend la main : il pourra dormir ou se recharger.'))return;
 busy=true;$('main').disabled=true;
 try{
  if(!b.ok){await cmd('w');await wait(1500);await cmd('s');await wait(500);await cmd('f');await wait(2500);}
  else if(b.mode!==3){if(b.mode!==2){await cmd('s');await wait(400);}await cmd('f');}
  else{await cmd(' ');await cmd('s');await wait(400);await cmd('x');}
 }finally{await wait(900);busy=false;$('main').disabled=false;}
}
let hold=null;
function holdStart(k,e){if(e)e.preventDefault();if(!canDrive()){nudge();return;}if(hold)clearInterval(hold);cmd(k);hold=setInterval(()=>cmd(k),400);}
function holdEnd(){if(hold){clearInterval(hold);hold=null;cmd(' ');}}
document.querySelectorAll('.pad button[data-k]').forEach(b=>{
 b.addEventListener('pointerdown',e=>holdStart(b.dataset.k,e));
 ['pointerup','pointercancel','pointerleave'].forEach(ev=>b.addEventListener(ev,holdEnd));
 b.addEventListener('contextmenu',e=>e.preventDefault());
});
window.addEventListener('pointerup',holdEnd);window.addEventListener('blur',holdEnd);
const KEYS={ArrowUp:'8',ArrowDown:'2',ArrowLeft:'4',ArrowRight:'6'};let keyDown=null;
window.addEventListener('keydown',e=>{if(e.target.tagName==='INPUT'||e.target.tagName==='SELECT')return;
 if(e.key===' '){e.preventDefault();holdEnd();cmd(' ');return;}
 const k=KEYS[e.key];if(!k)return;e.preventDefault();if(keyDown===e.key)return;keyDown=e.key;holdStart(k);});
window.addEventListener('keyup',e=>{if(e.key===keyDown){keyDown=null;holdEnd();}});
$('spd').addEventListener('input',()=>{$('spdv').textContent=$('spd').value+' mm/s';});
$('spd').addEventListener('change',()=>{fetch('/api/speed?v='+$('spd').value).catch(()=>{});});

const CHG={0:'sur batterie',1:'reconditionnement',2:'en charge',3:"charge d'entretien",4:'en attente de charge',5:'défaut de charge'};
const cm=mm=>(mm/10).toFixed(0)+' cm';
function setCls(el,c,on){el.classList.toggle(c,!!on);}
async function refresh(){
 let s;try{s=await (await fetch('/api/state')).json();}catch(e){$('dot').className='dot warn';$('top').textContent='carte injoignable…';return;}
 S=s;const b=s.robot,p=s.pose,r=s.radar,charge=b.ok&&(b.base||b.chg>0&&b.chg<4);
 const pct=b.qmax?Math.round(100*b.q/b.qmax):0;
 // état du robot et bouton principal
 let st,cls,act;
 if(!b.ok){st='Ne répond pas';cls='bad';act='Réveiller le robot';}
 else if(b.mode===3){st=s.driving?'Roule':'Prêt à rouler';cls='ok';act='Fin de session';}
 else if(charge){st='Sur sa base';cls='warn';act='Prendre la main';}
 else{st='Flèches bloquées';cls='warn';act='Prendre la main';}
 $('rstate').textContent=st;$('dot').className='dot '+cls;
 $('top').textContent=st+(b.ok?' · '+pct+' %':'');
 if(!busy){const m=$('main');m.textContent=act;m.className=b.ok&&b.mode===3?'ghost':'pri';}
 setCls($('pad'),'lock',!canDrive());
 $('drvhint').textContent=canDrive()?'Maintenez une flèche pour rouler ; le robot s\'arrête dès que vous relâchez. Au clavier : les flèches, espace pour arrêter.':(b.ok?'Les flèches sont bloquées tant que le robot n\'est pas en mode Safe : touchez « Prendre la main ».':'Le robot dort ou sa liaison est fermée : touchez « Réveiller le robot », ou appuyez d\'abord sur CLEAN sur le robot.');
 if(document.activeElement!==$('spd')){$('spd').value=s.speed;$('spdv').textContent=s.speed+' mm/s';}
 // distance mesurée
 let d='–',ds='capteur de distance à l\'arrêt';
 if(r.mode){
  if(r.absent){ds='le capteur ne réagit pas';}
  else if(r.mm<0||r.mm_age>2500){d='…';ds='mesure en cours';}
  else{d=r.mm>0?cm(r.mm):'> 4 m';ds=(r.mm>0?'':'rien à portée, ')+(r.a===0?'droit devant':'à '+Math.abs(r.a)+'° sur la '+(r.a>0?'gauche':'droite'));}
 }
 $('dist').textContent=d;$('distsub').textContent=ds;
 for(let k=0;k<3;k++)setCls($('rm'+k),'on',r.mode===k);
 // position
 if(p){const cap=((p.cap+180)%360+360)%360-180;
  $('tcap').textContent=cap.toFixed(0)+'°';$('tpos').textContent=(p.x/10).toFixed(0)+' ; '+(p.y/10).toFixed(0)+' cm';
  $('tdist').textContent=(p.dist/1000).toFixed(2).replace('.',',')+' m';$('tecart').textContent=cm(Math.hypot(p.x,p.y));}
 // alertes : toujours une pastille et un texte
 const al=[];
 if(b.ok){
  if(b.bump[0]||b.bump[1])al.push(['c','Pare-chocs touché'+(b.bump[0]&&b.bump[1]?'':b.bump[0]?' à gauche':' à droite')]);
  if(b.drop[0]||b.drop[1])al.push(['c','Roue soulevée']);
  if(b.cliff.some(v=>v<100))al.push(['c','Vide détecté sous le robot']);
 }
 if(r.mode&&r.securite&&r.front_mm>0&&r.front_mm<r.seuil*10&&r.age<1500)al.push(['c','Obstacle à '+cm(r.front_mm)+' devant : avance bloquée']);
 if(r.mode&&r.absent)al.push(['w','Le capteur de distance ne réagit pas']);
 if(p&&p.leve)al.push(['w','Robot soulevé : la position n\'est plus juste']);
 else if(p&&p.leves)al.push(['w','Robot soulevé '+p.leves+' fois : touchez « Nouveau départ »']);
 if(p&&p.sauts)al.push(['w',p.sauts+' déplacement(s) non compté(s) dans la position']);
 if(!s.imu.ok)al.push(['w','Gyroscope absent : cap calculé avec les roues']);
 if(b.ok&&pct<15)al.push(['w','Batterie faible']);
 $('alerts').innerHTML=al.map(a=>'<div class="al"><span class="ico'+(a[0]==='w'?' w':'')+'">!</span><span>'+a[1]+'</span></div>').join('');
 // tour sur place
 const t=s.tour,en=t&&(t.etat===1||t.etat===2);
 $('btour').textContent=en?'Arrêter le tour ('+Math.round(t.tourne)+'°)':'Tour sur place';setCls($('btour'),'on',en);
 // batterie
 $('sbat').textContent=b.ok?pct+' % · '+(CHG[b.chg]||''):'–';
 $('batbar').style.width=(b.ok?pct:0)+'%';$('meter').style.setProperty('--fill',pct<15?'var(--crit)':pct<30?'var(--warn)':'var(--accent)');
 $('v').textContent=b.ok?(b.v/1000).toFixed(2).replace('.',',')+' V':'–';$('i').textContent=b.ok?b.i+' mA':'–';
 $('t').textContent=b.ok?b.t+' °C':'–';$('mah').textContent=b.ok?b.q+' mAh':'–';
 $('bathint').textContent=b.ok?(b.i<-20?'À ce rythme, environ '+(b.q/-b.i).toFixed(b.q/-b.i<10?1:0).replace('.',',')+' h de réserve. ':'')+'Capacité notée par le robot : '+b.qmax+' mAh.':'Aucune lecture récente.';
 // capteurs
 setCls($('bl'),'hit',b.ok&&b.bump[0]);setCls($('br'),'hit',b.ok&&b.bump[1]);
 setCls($('wl'),'hit',b.ok&&b.drop[0]);setCls($('wr'),'hit',b.ok&&b.drop[1]);
 [...$('lb').children].forEach((e,k)=>setCls(e,'seen',b.ok&&b.light[k]>60));
 [...$('cl').children].forEach((e,k)=>{setCls(e,'hit',b.ok&&b.cliff[k]<100);setCls(e,'fine',b.ok&&b.cliff[k]>=100);});
 $('ssens').textContent=!b.ok?'–':(b.bump[0]||b.bump[1]||b.drop[0]||b.drop[1]||b.cliff.some(v=>v<100))?'à regarder':'rien à signaler';
 $('cliff').textContent=b.ok?b.cliff.join(' · '):'–';$('light').textContent=b.ok?b.light.join(' · '):'–';
 $('enc').textContent=b.ok?b.enc[0]+' · '+b.enc[1]:'–';$('cur').textContent=b.ok&&b.cur?b.cur[0]+' · '+b.cur[1]+' mA':'–';
 $('srad').textContent=['arrêté','regarde devant','balaie'][r.mode]||'';
 $('sgyro').textContent=s.imu.ok?(s.imu.cal?'gyroscope : recalage…':'gyroscope '+s.imu.yaw.toFixed(0)+'°'):'gyroscope absent';
 setCls($('ba'),'on',s.keep);setCls($('bj'),'on',s.csv);
 $('foot').textContent=s.ver+' · en marche depuis '+Math.round(s.ms/60000)+' min · '+s.host+'.local'+(s.robot_redem?' · robot vu se réveiller '+s.robot_redem+' fois':'');
 syncPose();syncCarte();drawMap();
}

// ---- Tracé et obstacles : seuls les points nouveaux sont redemandés ----
let pz={gen:0,pts:[]},pbusy=false,ct={gen:0,next:0,pts:[],dx:0},cbusy=false;
async function syncPose(){const p=S.pose;if(!p||pbusy||(p.gen===pz.gen&&p.n===pz.pts.length))return;pbusy=true;
 try{const r=await (await fetch('/api/pose?gen='+pz.gen+'&from='+pz.pts.length)).json();
  if(r.from===0)pz.pts=r.points;else if(r.from===pz.pts.length)for(const q of r.points)pz.pts.push(q);
  pz.gen=r.gen;}catch(e){}
 pbusy=false;drawMap();}
async function syncCarte(){const c=S.carte;if(!c||cbusy||(c.gen===ct.gen&&c.total===ct.next))return;cbusy=true;
 try{const r=await (await fetch('/api/carte?gen='+ct.gen+'&from='+ct.next)).json();
  if(r.gen!==ct.gen){ct.pts=[];ct.gen=r.gen;}
  for(const q of r.points)ct.pts.push(q);
  if(ct.pts.length>6000)ct.pts.splice(0,ct.pts.length-6000);
  ct.next=r.from+r.points.length;ct.dx=r.dx;}catch(e){}
 cbusy=false;drawMap();}
async function poseZero(){if(!confirm('Nouveau départ : le robot devient le point zéro, le tracé et les obstacles sont effacés.'))return;
 try{await fetch('/api/pose?zero=1');}catch(e){}pz={gen:0,pts:[]};ct={gen:0,next:0,pts:[],dx:ct.dx};}
async function carteClear(){try{await fetch('/api/carte?effacer=1');}catch(e){}ct={gen:0,next:0,pts:[],dx:ct.dx};drawMap();}
async function tour(){
 const t=S&&S.tour;if(t&&(t.etat===1||t.etat===2)){fetch('/api/tour?stop=1').catch(()=>{});return;}
 if(!canDrive()){nudge();return;}
 if(!confirm('Le robot va tourner sur lui-même pendant 13 secondes en mesurant les distances. Rien à moins de 40 cm autour de lui ?'))return;
 try{const r=await (await fetch('/api/tour?go=1')).json();if(r.etat===4)alert('Tour impossible : '+r.raison);}catch(e){}
}

// ---- Carte : vue de dessus et vue 3D ----
let view=0,follow=false,cam={az:Math.PI*1.2,el:.62,k:1};
function setView(v){view=v;setCls($('vw0'),'on',v===0);setCls($('vw1'),'on',v===1);$('map').style.touchAction=v?'none':'pan-y';
 $('maphint').textContent=v?'Vue 3D : faites glisser pour tourner autour, pincez ou utilisez la molette pour approcher. Les poteaux sont les obstacles vus par le capteur.':'Le haut de la carte est l\'avant du robot au départ. « Tour sur place » : le robot tourne sur lui-même et dessine ce qui l\'entoure.';drawMap();}
function toggleFit(){follow=!follow;setCls($('fit'),'on',follow);drawMap();}
function extent(){const p=(S&&S.pose)||{x:0,y:0};let x0=Math.min(0,p.x),x1=Math.max(0,p.x),y0=Math.min(0,p.y),y1=Math.max(0,p.y);
 for(const a of[pz.pts,ct.pts])for(const q of a){if(q[0]<x0)x0=q[0];if(q[0]>x1)x1=q[0];if(q[1]<y0)y0=q[1];if(q[1]>y1)y1=q[1];}
 return{x0,x1,y0,y1};}
function gridStep(s,px){for(const k of[100,250,500,1000,2000,5000,10000])if(k*s>=px)return k;return 20000;}
function beam(){const r=S.radar,p=S.pose;if(!r.mode||r.mm<0||r.mm_age>1500||r.absent)return null;
 const c=p.cap*RAD,a=c+r.a*RAD,o=[p.x+ct.dx*Math.cos(c),p.y+ct.dx*Math.sin(c)],len=r.mm>0?r.mm:1200;
 return{o,h:[o[0]+len*Math.cos(a),o[1]+len*Math.sin(a)],hit:r.mm>0,close:r.securite&&r.mm>0&&Math.abs(r.a)<=15&&r.mm<r.seuil*10,mm:r.mm};}
function drawMap(){
 const c=$('map'),dpr=Math.min(2,window.devicePixelRatio||1),W=c.clientWidth,H=c.clientHeight;if(!W||!H)return;
 if(c.width!==Math.round(W*dpr)||c.height!==Math.round(H*dpr)){c.width=Math.round(W*dpr);c.height=Math.round(H*dpr);}
 const x=c.getContext('2d');x.setTransform(dpr,0,0,dpr,0,0);x.clearRect(0,0,W,H);x.fillStyle=C.surface2;x.fillRect(0,0,W,H);
 x.lineJoin='round';x.lineCap='round';x.font='11px system-ui,sans-serif';
 if(!S||!S.pose){x.fillStyle=C.mut;x.textAlign='center';x.fillText('en attente de la carte…',W/2,H/2);return;}
 (view?draw3D:draw2D)(x,W,H);
}
function draw2D(x,W,H){
 const p=S.pose,e=extent();let s,mx,my;
 if(follow){s=Math.min(W,H)/3000;mx=p.x;my=p.y;}
 else{s=Math.min(H/Math.max(2000,e.x1-e.x0+900),W/Math.max(2000,e.y1-e.y0+900));mx=(e.x0+e.x1)/2;my=(e.y0+e.y1)/2;}
 const X=wy=>W/2-(wy-my)*s,Y=wx=>H/2-(wx-mx)*s,g=gridStep(s,44);
 x.lineWidth=1;
 for(let k=Math.ceil((mx-H/2/s)/g);k*g<=mx+H/2/s;k++){x.strokeStyle=k?C.line:C.axis;x.beginPath();x.moveTo(0,Y(k*g));x.lineTo(W,Y(k*g));x.stroke();}
 for(let k=Math.ceil((my-W/2/s)/g);k*g<=my+W/2/s;k++){x.strokeStyle=k?C.line:C.axis;x.beginPath();x.moveTo(X(k*g),0);x.lineTo(X(k*g),H);x.stroke();}
 // obstacles vus
 x.fillStyle=C.s2;x.globalAlpha=.85;for(const q of ct.pts){x.beginPath();x.arc(X(q[1]),Y(q[0]),2.3,0,7);x.fill();}x.globalAlpha=1;
 // tracé
 if(pz.pts.length){x.strokeStyle=C.s1;x.lineWidth=2;x.beginPath();pz.pts.forEach((q,k)=>k?x.lineTo(X(q[1]),Y(q[0])):x.moveTo(X(q[1]),Y(q[0])));x.lineTo(X(p.y),Y(p.x));x.stroke();}
 // départ
 x.strokeStyle=C.ink2;x.lineWidth=1.5;x.beginPath();x.arc(X(0),Y(0),4,0,7);x.stroke();
 // faisceau du capteur de distance
 const b=beam();
 if(b){const col=b.close?C.crit:C.s3;x.strokeStyle=col;x.lineWidth=1.5;x.globalAlpha=b.hit?.75:.35;x.beginPath();x.moveTo(X(b.o[1]),Y(b.o[0]));x.lineTo(X(b.h[1]),Y(b.h[0]));x.stroke();x.globalAlpha=1;
  if(b.hit){const hx=X(b.h[1]),hy=Y(b.h[0]);x.fillStyle=C.surface2;x.beginPath();x.arc(hx,hy,6.5,0,7);x.fill();x.fillStyle=col;x.beginPath();x.arc(hx,hy,4.5,0,7);x.fill();
   x.fillStyle=C.ink2;x.textAlign=hx>W-70?'right':'left';x.fillText(cm(b.mm),hx+(hx>W-70?-10:10),hy+4);}}
 // robot
 const rx=X(p.y),ry=Y(p.x),r=Math.max(8,170*s),t=p.cap*RAD,dir=a=>[rx-r*Math.sin(a),ry-r*Math.cos(a)];
 x.fillStyle=C.surface;x.strokeStyle=S.robot.ok?C.s3:C.mut;x.lineWidth=2;x.beginPath();x.arc(rx,ry,r,0,7);x.fill();x.stroke();
 let f=dir(t);x.beginPath();x.moveTo(rx,ry);x.lineTo(f[0],f[1]);x.stroke();
 const bm=S.robot.ok?S.robot.bump:[0,0];
 [[bm[0],8,82],[bm[1],-82,-8]].forEach(a=>{if(!a[0])return;x.strokeStyle=C.crit;x.lineWidth=4;x.beginPath();for(let d=a[1];d<=a[2];d+=6){const q=[rx-(r+3)*Math.sin(t+d*RAD),ry-(r+3)*Math.cos(t+d*RAD)];d===a[1]?x.moveTo(q[0],q[1]):x.lineTo(q[0],q[1]);}x.stroke();});
 $('scale').textContent='Carreau : '+(g<1000?g/10+' cm':g/1000+' m');
}
function draw3D(x,W,H){
 const p=S.pose,e=extent(),tgt=follow?[p.x,p.y,0]:[(e.x0+e.x1)/2,(e.y0+e.y1)/2,0];
 const span=follow?2200:Math.max(2200,e.x1-e.x0+600,e.y1-e.y0+600),D=span*1.05*cam.k,F=Math.min(W,H)*1.05;
 const ce=Math.cos(cam.el),se=Math.sin(cam.el),ca=Math.cos(cam.az),sa=Math.sin(cam.az);
 const cp=[tgt[0]+D*ce*ca,tgt[1]+D*ce*sa,D*se],fw=[-ce*ca,-ce*sa,-se],rt=[-sa,ca,0],up=[-ca*se,-sa*se,ce];
 const P=(wx,wy,wz)=>{const v=[wx-cp[0],wy-cp[1],wz-cp[2]],z=v[0]*fw[0]+v[1]*fw[1]+v[2]*fw[2];if(z<60)return null;
  return[W/2+F*(v[0]*rt[0]+v[1]*rt[1])/z,H*.52-F*(v[0]*up[0]+v[1]*up[1]+v[2]*up[2])/z,z];};
 const seg=(a,b)=>{if(a&&b){x.beginPath();x.moveTo(a[0],a[1]);x.lineTo(b[0],b[1]);x.stroke();}};
 // sol quadrillé
 const g=gridStep(F/D,34),hs=Math.ceil(span*.8/g)*g,gx0=Math.round(tgt[0]/g)*g,gy0=Math.round(tgt[1]/g)*g;
 x.lineWidth=1;
 for(let k=-hs;k<=hs;k+=g){x.strokeStyle=(gx0+k===0)?C.axis:C.line;seg(P(gx0+k,gy0-hs,0),P(gx0+k,gy0+hs,0));x.strokeStyle=(gy0+k===0)?C.axis:C.line;seg(P(gx0-hs,gy0+k,0),P(gx0+hs,gy0+k,0));}
 // tracé au sol
 x.strokeStyle=C.s1;x.lineWidth=2;x.beginPath();let on=false;
 for(const q of pz.pts.concat([[p.x,p.y]])){const a=P(q[0],q[1],0);if(!a){on=false;continue;}on?x.lineTo(a[0],a[1]):x.moveTo(a[0],a[1]);on=true;}x.stroke();
 const o0=P(0,0,0);if(o0){x.strokeStyle=C.ink2;x.lineWidth=1.5;x.beginPath();x.ellipse(o0[0],o0[1],5,5*se,0,0,7);x.stroke();}
 // obstacles (poteaux) et robot, du plus loin au plus proche
 const items=[];
 for(const q of ct.pts){const a=P(q[0],q[1],0),b=P(q[0],q[1],220);if(a&&b)items.push([a[2],0,a,b]);}
 const rc=P(p.x,p.y,45);if(rc)items.push([rc[2],1]);
 items.sort((a,b)=>b[0]-a[0]);
 for(const it of items){
  if(it[1]===0){x.strokeStyle=C.s2;x.globalAlpha=.5;x.lineWidth=1.5;seg(it[2],it[3]);x.globalAlpha=.95;x.fillStyle=C.s2;x.beginPath();x.arc(it[3][0],it[3][1],2.3,0,7);x.fill();x.globalAlpha=1;continue;}
  // robot : un cylindre de 34 cm de large et 9 cm de haut
  const ring=z=>{const a=[];for(let k=0;k<32;k++){const t=k*Math.PI/16,q=P(p.x+170*Math.cos(t),p.y+170*Math.sin(t),z);if(!q)return null;a.push(q);}return a;};
  const lo=ring(0),hi=ring(92);if(!lo||!hi)continue;
  const poly=(a,fill)=>{x.beginPath();a.forEach((q,k)=>k?x.lineTo(q[0],q[1]):x.moveTo(q[0],q[1]));x.closePath();if(fill){x.fillStyle=fill;x.fill();}x.stroke();};
  const ext=a=>{let l=a[0],r=a[0];for(const q of a){if(q[0]<l[0])l=q;if(q[0]>r[0])r=q;}return[l,r];};
  x.strokeStyle=S.robot.ok?C.s3:C.mut;x.lineWidth=2;
  poly(lo,C.surface);const el=ext(lo),eh=ext(hi);
  x.beginPath();x.moveTo(el[0][0],el[0][1]);x.lineTo(eh[0][0],eh[0][1]);x.lineTo(eh[1][0],eh[1][1]);x.lineTo(el[1][0],el[1][1]);x.closePath();x.fillStyle=C.surface;x.fill();
  seg(el[0],eh[0]);seg(el[1],eh[1]);poly(hi,C.surface);
  const t=p.cap*RAD;seg(P(p.x,p.y,92),P(p.x+170*Math.cos(t),p.y+170*Math.sin(t),92));
  const b=beam();
  if(b){const col=b.close?C.crit:C.s3,a=P(b.o[0],b.o[1],130),h=P(b.h[0],b.h[1],130);
   x.strokeStyle=col;seg(P(b.o[0],b.o[1],92),a);x.lineWidth=1.5;x.globalAlpha=b.hit?.75:.35;seg(a,h);x.globalAlpha=1;
   if(a){x.fillStyle=col;x.beginPath();x.arc(a[0],a[1],3.5,0,7);x.fill();}
   if(b.hit&&h){x.fillStyle=C.surface2;x.beginPath();x.arc(h[0],h[1],6.5,0,7);x.fill();x.fillStyle=col;x.beginPath();x.arc(h[0],h[1],4.5,0,7);x.fill();x.fillStyle=C.ink2;x.textAlign='left';x.fillText(cm(b.mm),h[0]+10,h[1]+4);}}
 }
 $('scale').textContent='Carreau : '+(g<1000?g/10+' cm':g/1000+' m');
}
// tourner et approcher la vue 3D
{const c=$('map'),pts=new Map();let pinch=0;
 c.addEventListener('pointerdown',e=>{if(!view)return;c.setPointerCapture(e.pointerId);pts.set(e.pointerId,[e.clientX,e.clientY]);pinch=0;});
 c.addEventListener('pointermove',e=>{if(!view||!pts.has(e.pointerId))return;const o=pts.get(e.pointerId);pts.set(e.pointerId,[e.clientX,e.clientY]);
  if(pts.size===1){cam.az-=(e.clientX-o[0])*.009;cam.el=Math.max(.12,Math.min(1.5,cam.el+(e.clientY-o[1])*.007));}
  else{const a=[...pts.values()],d=Math.hypot(a[0][0]-a[1][0],a[0][1]-a[1][1]);if(pinch)cam.k=Math.max(.25,Math.min(4,cam.k*pinch/d));pinch=d;}
  drawMap();});
 const end=e=>{pts.delete(e.pointerId);pinch=0;};c.addEventListener('pointerup',end);c.addEventListener('pointercancel',end);
 c.addEventListener('wheel',e=>{if(!view)return;e.preventDefault();cam.k=Math.max(.25,Math.min(4,cam.k*(e.deltaY>0?1.1:.9)));drawMap();},{passive:false});}
window.addEventListener('resize',drawMap);
matchMedia('(prefers-color-scheme:dark)').addEventListener('change',()=>{loadColors();drawMap();if(rd)drawRadar(rd);});

// ---- Capteur de distance : réglages et demi-cercle ----
let rd=null;
async function radar(q){try{drawRadar(await (await fetch('/api/radar?'+q)).json());}catch(e){}}
function drawRadar(r){
 rd=r;
 if(document.activeElement!==$('rseuil')){$('rseuil').value=r.seuil;$('rseuilv').textContent=r.seuil+' cm';}
 $('rsec').checked=r.securite;$('rauto').checked=r.auto;$('rinv').checked=r.inv;$('rpas').value=r.pas;$('ramp').value=r.amplitude;$('rmax').value=r.butee;
 const c=$('rc'),x=c.getContext('2d'),W=c.width,H=c.height,cx=W/2,cy=H-16,R=H-32,port=+$('rport').value;
 const pt=(a,d)=>[cx-R*d*Math.sin(a*RAD),cy-R*d*Math.cos(a*RAD)];
 x.clearRect(0,0,W,H);x.font='10px system-ui,sans-serif';
 x.fillStyle=C.surface2;x.beginPath();x.moveTo(cx,cy);x.arc(cx,cy,R,Math.PI,2*Math.PI);x.closePath();x.fill();
 x.strokeStyle=C.line;x.lineWidth=1;x.setLineDash([]);
 for(let k=1;k<=4;k++){x.beginPath();x.arc(cx,cy,R*k/4,Math.PI,2*Math.PI);x.stroke();}
 for(const a of[-60,-30,0,30,60]){const q=pt(a,1);x.beginPath();x.moveTo(cx,cy);x.lineTo(q[0],q[1]);x.stroke();}
 x.fillStyle=C.mut;x.textAlign='left';for(let k=1;k<=4;k++)x.fillText(Math.round(port*k/4)+'',cx+3,cy-R*k/4+10);
 x.textAlign='center';x.fillText('gauche',28,cy+12);x.fillText('droite',W-28,cy+12);
 x.strokeStyle=C.crit;x.setLineDash([4,3]);x.beginPath();x.arc(cx,cy,R*Math.min(1,r.seuil/port),Math.PI,2*Math.PI);x.stroke();x.setLineDash([]);
 if(r.butee<80){x.strokeStyle=C.mut;x.lineWidth=1.5;for(const a of[-r.butee,r.butee]){const q=pt(a,1);x.beginPath();x.moveTo(cx,cy);x.lineTo(q[0],q[1]);x.stroke();}}
 if(r.mode){const q=pt(r.servo,1);x.strokeStyle=C.s3;x.lineWidth=2;x.beginPath();x.moveTo(cx,cy);x.lineTo(q[0],q[1]);x.stroke();}
 for(const p of r.points){const v=p[1]/10,al=Math.max(.25,1-p[2]/8000);x.globalAlpha=al;
  if(v<=0){const q=pt(p[0],.985);x.fillStyle=C.mut;x.beginPath();x.arc(q[0],q[1],2,0,7);x.fill();continue;}
  const q=pt(p[0],Math.min(1,v/port));x.fillStyle=v<r.seuil?C.crit:C.s2;x.beginPath();x.arc(q[0],q[1],v>port?3:4.5,0,7);x.fill();}
 x.globalAlpha=1;x.fillStyle=C.ink;x.beginPath();x.arc(cx,cy,4,0,7);x.fill();
}
$('rseuil').addEventListener('input',()=>{$('rseuilv').textContent=$('rseuil').value+' cm';});
$('rseuil').addEventListener('change',()=>radar('seuil='+$('rseuil').value));
$('rc').addEventListener('click',e=>{const c=$('rc'),b=c.getBoundingClientRect(),sx=c.width/b.width,sy=c.height/b.height;
 const dx=(e.clientX-b.left)*sx-c.width/2,dy=(c.height-16)-(e.clientY-b.top)*sy;if(dy<5)return;
 const lim=(rd&&rd.butee)||80,a=Math.max(-lim,Math.min(lim,Math.round(Math.atan2(-dx,dy)/RAD)));radar('mode=fixe&angle='+a);});
$('drad').addEventListener('toggle',()=>{if($('drad').open)radar('');});

// ---- Console ----
let seq=0;
async function pollLog(){
 try{const r=await (await fetch('/api/log?since='+seq)).json();
  if(r.lines.length){const L=$('log'),atEnd=L.scrollHeight-L.scrollTop-L.clientHeight<30;
   r.lines.forEach((l,k)=>{if(r.from+k<seq)return;const d=document.createElement('div');d.textContent=l;L.appendChild(d);});
   while(L.children.length>120)L.removeChild(L.firstChild);
   if(atEnd)L.scrollTop=L.scrollHeight;}
  seq=r.seq;}catch(e){}
}
setInterval(()=>{if($('dlog').open)pollLog();},1000);
setInterval(()=>{if($('drad').open)radar('');},700);
setInterval(refresh,500);refresh();
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
