// =====================================================================
// RazorGauge - ALLINEAMENTO GUIDATO DEL LASER (pagina web http://<ip-del-master>/align)
// 29/10/2026 - per la sede laser v3 (Picotronic LFD650-1-12(9x20): cono + 2 grani + O-ring, poi epossidica)
//
// Cosa fa: mentre la pagina /align e' aperta il task del sensore smette di misurare e acquisisce
// solo il fascio (laser - buio, esposizione regolata da sola per non saturare). Calcola:
//   - baricentro del profilo lungo la fila di pixel (finestra SIMMETRICA attorno al centro fisico 63.5)
//   - segnale medio nella finestra (serve per la direzione di traverso, che il sensore non vede)
//   - larghezza a meta' altezza, picco, pixel saturi, bilancio sinistra/destra
// La pagina traduce questi numeri in istruzioni esplicite: quale grano, in che verso, di quanto.
//
// INTEGRAZIONE nel master col laser (master_razorgauge, stessa struttura della 0.6.0 / 1.0.x):
//   1) #include "gauge_align.inc"  DOPO il codice del gauge (gCapture, gAverage, gDark, G_NPIX ...)
//      e PRIMA di gaugeTask()
//   2) in gaugeTask(), come prima istruzione del for(;;):
//          if (gAlignActive()) { gAlignStep(); continue; }
//      (le richieste gauge_* in coda vengono servite dopo l'uscita dal modo allineamento)
//   3) in gaugeHttpSetup():   gaugeAlignHttpSetup();
// Nessuna modifica al protocollo WebSocket verso l'app WPF. Il modo allineamento si spegne da solo
// 5 s dopo l'ultima richiesta della pagina (pagina chiusa = misura normale).
// Al termine: l'esposizione resta quella trovata dall'allineamento -> rifare gauge_dark e gauge_ref.
// =====================================================================

#ifndef ALIGN_PIX_FIRST
#define ALIGN_PIX_FIRST 16     // primo pixel utile (sensore attuale: 0-13 morti). Scheda TSL1401CL nuova: 2
#endif
#ifndef ALIGN_PIX_LAST
#define ALIGN_PIX_LAST 125     // ultimo pixel utile
#endif
static const float AL_CENTER = (G_NPIX - 1) / 2.0f;        // 63.5: centro fisico della fila
static const int   AL_HALF   = (int)min(AL_CENTER - ALIGN_PIX_FIRST, ALIGN_PIX_LAST - AL_CENTER);   // finestra simmetrica
static const int   AL_LO = (int)ceilf(AL_CENTER - AL_HALF), AL_HI = (int)floorf(AL_CENTER + AL_HALF);

struct AlignData {
  uint32_t n;            // numero acquisizione
  uint32_t exp;          // esposizione us
  float    peak;         // mV (laser - buio) nella finestra
  float    mean;         // mV medi nella finestra
  float    c;            // baricentro (indice pixel)
  float    fwhm;         // pixel sopra meta' picco (limitata dalla finestra)
  float    bal;          // (destra - sinistra) / totale, nella finestra
  int      sat;          // pixel saturi (grezzi >= G_MV_SAT)
  bool     dark;         // buio acquisito con l'esposizione attuale
  int16_t  p[G_NPIX];    // profilo laser - buio (mV)
};
static AlignData gAl;
static float     gAlDark[G_NPIX];
static uint32_t  gAlDarkExp = 0;
static volatile uint32_t gAlLastHttpMs = 0;

static bool gAlignActive() {
  return gAlLastHttpMs && (millis() - gAlLastHttpMs) < 5000;
}

static void gAlignStep() {
  if (gAlDarkExp != gExposureUs) {                          // buio con la stessa posa
    gAverage(false, gAlDark, 4);
    gAlDarkExp = gExposureUs;
  }
  gAverage(true, gAcc, 2);
  AlignData a; a.n = gAl.n + 1; a.exp = gExposureUs; a.dark = true;
  float pk = 0, sum = 0, mom = 0, wsum = 0, L = 0, R = 0; int sat = 0;
  for (int i = 0; i < G_NPIX; i++) {
    float s = gAcc[i] - gAlDark[i];
    a.p[i] = (int16_t)constrain(lroundf(s), -32000L, 32000L);
    if (gAcc[i] >= G_MV_SAT && i >= AL_LO && i <= AL_HI) sat++;
    if (i >= AL_LO && i <= AL_HI) { pk = max(pk, s); sum += max(s, 0.0f); if (i < AL_CENTER) L += max(s, 0.0f); else R += max(s, 0.0f); }
  }
  int nw = AL_HI - AL_LO + 1, nhalf = 0;
  for (int i = AL_LO; i <= AL_HI; i++) {
    float s = a.p[i];
    if (s > 0.10f * pk) { float w = s - 0.10f * pk; mom += w * i; wsum += w; }   // soglia al 10%: niente rumore nelle code
    if (s >= 0.5f * pk) nhalf++;
  }
  a.peak = pk; a.mean = sum / nw; a.sat = sat; a.fwhm = nhalf;
  a.c = wsum > 0 ? mom / wsum : AL_CENTER;
  a.bal = (L + R) > 0 ? (R - L) / (L + R) : 0;
  portENTER_CRITICAL(&gMux); gAl = a; portEXIT_CRITICAL(&gMux);
  // esposizione automatica: picco tra 55% e 80% della zona lineare (G_MV_SAT); il buio si rifa' alla prossima
  float hi = 0.80f * G_MV_SAT, lo = 0.55f * G_MV_SAT;
  if ((sat > 0 || pk > hi) && gExposureUs > G_EXP_MIN) gExposureUs = max(G_EXP_MIN, (uint32_t)(gExposureUs * 0.75f));
  else if (pk < lo && pk > 30 && gExposureUs < G_EXP_MAX) gExposureUs = min(G_EXP_MAX, (uint32_t)(gExposureUs * 1.25f) + 1);
  vTaskDelay(pdMS_TO_TICKS(80));
}

static void gaugeAlignJson() {
  gAlLastHttpMs = millis();
  AlignData a; portENTER_CRITICAL(&gMux); a = gAl; portEXIT_CRITICAL(&gMux);
  String s; s.reserve(1400);
  char b[300];
  snprintf(b, sizeof(b), "{\"n\":%u,\"exp\":%u,\"peak\":%.1f,\"mean\":%.1f,\"c\":%.2f,\"center\":%.1f,\"fwhm\":%.0f,\"bal\":%.4f,"
           "\"sat\":%d,\"lo\":%d,\"hi\":%d,\"mvsat\":%d,\"pxmm\":%.4f,\"p\":[",
           (unsigned)a.n, (unsigned)a.exp, a.peak, a.mean, a.c, AL_CENTER, a.fwhm, a.bal, a.sat, AL_LO, AL_HI, (int)G_MV_SAT, G_PIXEL_MM);
  s += b;
  for (int i = 0; i < G_NPIX; i++) { s += String((int)a.p[i]); if (i < G_NPIX - 1) s += ','; }
  s += "]}";
  server.send(200, "application/json", s);
}

static const char GAUGE_ALIGN_HTML[] PROGMEM = R"HTML(<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>RazorGauge - allineamento laser</title>
<style>
body{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:0;background:#101418;color:#e8eef3}
header{padding:10px 16px;background:#1b232b;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
header b{font-size:18px} .st{font-size:13px;color:#9fb0bf}
main{padding:12px 16px;max-width:1000px;margin:auto}
.steps{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}
.steps span{padding:4px 10px;border-radius:12px;background:#26313b;font-size:13px;color:#9fb0bf}
.steps span.on{background:#2f7dd1;color:#fff} .steps span.ok{background:#2e8b57;color:#fff}
#cmd{font-size:28px;font-weight:700;line-height:1.25;padding:18px;border-radius:10px;background:#1e2a35;min-height:90px}
#cmd.ok{background:#1f5135} #cmd.warn{background:#5a3b12} #cmd.err{background:#5a1717}
#sub{font-size:16px;color:#c7d3dd;margin:8px 2px 12px}
.arrow{font-size:46px;display:inline-block;margin-right:10px;vertical-align:middle}
canvas{width:100%;height:220px;background:#0b0f13;border-radius:8px}
.row{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0}
.k{background:#1b232b;border-radius:8px;padding:8px 12px;min-width:120px}
.k i{display:block;font-style:normal;font-size:12px;color:#8fa2b3} .k b{font-size:20px}
button{font-size:18px;padding:12px 20px;border-radius:8px;border:0;background:#2f7dd1;color:#fff;margin:4px 8px 4px 0;cursor:pointer}
button.sec{background:#3a4652} button:disabled{opacity:.4}
.bar{height:16px;background:#26313b;border-radius:8px;overflow:hidden;margin-top:4px} .bar>div{height:100%;background:#2e8b57}
small{color:#8fa2b3}
</style></head><body>
<header><b>Allineamento laser</b><span class="st" id="st">connessione...</span></header>
<main>
<div class="steps" id="steps"></div>
<div id="cmd">...</div>
<div id="sub"></div>
<div id="btns"></div>
<canvas id="cv" width="1000" height="220"></canvas>
<div class="row">
 <div class="k"><i>baricentro (pixel)</i><b id="kc">-</b></div>
 <div class="k"><i>scostamento</i><b id="ko">-</b></div>
 <div class="k"><i>segnale medio</i><b id="km">-</b><div class="bar"><div id="bm" style="width:0"></div></div></div>
 <div class="k"><i>larghezza (px a meta' altezza)</i><b id="kw">-</b></div>
 <div class="k"><i>picco / esposizione</i><b id="kp">-</b></div>
</div>
<small>Grano FRONTALE = quello raggiungibile dal foro nel coperchio (sposta il fascio lungo la fila di pixel).
Grano LATERALE = quello sul fianco della torre verso il rullo (sposta il fascio di traverso, lungo la coda di topo).
Chiave esagonale 1,5 mm. Prima di iniziare: laser acceso da almeno 5 minuti, coperchio montato, nessuna coda di topo nel canale.</small>
</main>
<script>
var TOLX=4;   // tolleranza lungo la fila: 4 px = 0.25 mm (il fascio e largo ~15 mm, la fila 8 mm)
var ST=['Fascio','Ellisse','Verso grano frontale','Lungo la fila','Di traverso','Stabilita'];
var S={step:0,last:null,hist:[],wbest:0,sx:+localStorage.getItem('al_sx')||0,sens:+localStorage.getItem('al_sens')||0,
       ref:null,sm:0,pos:0,ipmax:0,A:null,B:null,phase:0,stab0:null,okSince:0,busy:false};
function $(i){return document.getElementById(i)}
function avg(k,n){var h=S.hist.slice(-n);var s=0;h.forEach(function(d){s+=d[k]});return h.length?s/h.length:0}
function steps(){var h='';ST.forEach(function(t,i){h+='<span class="'+(i<S.step?'ok':(i==S.step?'on':''))+'">'+(i+1)+'. '+t+'</span>'});$('steps').innerHTML=h}
function say(cls,txt,sub,btn){$('cmd').className=cls||'';$('cmd').innerHTML=txt;$('sub').innerHTML=sub||'';$('btns').innerHTML=btn||''}
function go(n){S.step=n;S.okSince=0;S.phase=0;steps();}
function wait(ms){return new Promise(function(r){setTimeout(r,ms)})}
// media di ~1.5 s di misure dopo 0.8 s di assestamento
async function settle(){S.busy=true;await wait(800);S.hist=[];await wait(1500);S.busy=false;return {c:avg('c',8),m:avg('mean',8)}}
function eighths(px){return S.sens?Math.abs(px)/S.sens:0}
function frac(e){if(e<0.4)return 'un tocco (meno di 1/16 di giro)';if(e<0.75)return '1/16 di giro';var n=Math.round(e);return n+(n==1?' ottavo':' ottavi')+' di giro'}
function draw(d){var c=$('cv'),g=c.getContext('2d'),W=c.width,H=c.height;g.clearRect(0,0,W,H);
 var mx=Math.max(d.mvsat,10);g.fillStyle='#16324a';g.fillRect(d.lo/128*W,0,(d.hi-d.lo+1)/128*W,H);
 g.strokeStyle='#ff5050';g.beginPath();g.moveTo(d.center/128*W+W/256,0);g.lineTo(d.center/128*W+W/256,H);g.stroke();
 g.strokeStyle='#3fd17a';g.beginPath();g.moveTo(d.c/128*W+W/256,0);g.lineTo(d.c/128*W+W/256,H);g.stroke();
 g.fillStyle='#e8c040';for(var i=0;i<128;i++){var v=Math.max(0,d.p[i])/mx*H;g.fillRect(i/128*W+1,H-v,W/128-2,v)}
 g.fillStyle='#9fb0bf';g.font='14px sans-serif';g.fillText('rosso = centro del sensore, verde = baricentro del fascio, zona blu = pixel usati',8,16)}
function onData(d){S.last=d;S.hist.push(d);if(S.hist.length>60)S.hist.shift();draw(d);
 var off=d.c-d.center;$('kc').textContent=d.c.toFixed(1);$('ko').textContent=(off>=0?'+':'')+off.toFixed(1)+' px  ('+(off*d.pxmm).toFixed(2)+' mm)';
 $('km').textContent=d.mean.toFixed(0)+' mV';S.sm=Math.max(S.sm,avg('mean',5));$('bm').style.width=(S.sm?Math.min(100,100*avg('mean',5)/S.sm):0)+'%';
 $('kw').textContent=d.fwhm;$('kp').textContent=d.peak.toFixed(0)+' mV / '+d.exp+' us';
 $('st').textContent='acquisizione n. '+d.n+(d.sat?'  -  SATURO':'');
 if(!S.busy)logic(d,off)}
function logic(d,off){
 if(d.peak<120){say('err','Nessun fascio sul sensore','Controlla: laser alimentato (filo rosso = +), JP2 su 3,3 V, cavo J5. Se il laser e acceso il fascio puo essere tutto fuori dal chip: allenta entrambi i grani di mezzo giro e riprova.');return}
 if(d.sat){say('warn','Fascio troppo forte: attendo che l esposizione scenda...','L esposizione si regola da sola. Se resta saturo a 2 us serve un filtro ND.');return}
 if(S.step==0){go(1);return}
 if(S.step==1){var w=avg('fwhm',4);S.wbest=Math.max(S.wbest,w);
  say(w>=S.wbest-1?'ok':'', '<span class="arrow">&#8635;</span>RUOTA il laser sul suo asse (grani allentati) finche la LARGHEZZA e massima',
   'Larghezza ora: <b>'+w.toFixed(0)+' px</b>  -  massima trovata: <b>'+S.wbest.toFixed(0)+' px</b>. Il punto e ovale: quando e massima, il lato lungo dell ovale e lungo la fila di pixel. Se la larghezza riempie tutta la zona blu va bene comunque.',
   '<button onclick="go(S.sx?3:2)">Fatto: ellisse orientata</button><button class="sec" onclick="S.wbest=0">Azzera massimo</button>');return}
 if(S.step==2){say('','<span class="arrow">&#8635;</span>Grano FRONTALE: STRINGI (senso orario) di 1/8 di giro, poi premi il pulsante',
   'Serve una volta sola: capisco in che verso si muove il fascio e di quanto per ogni ottavo di giro. Prima avvicina il grano finche tocca il laser.',
   '<button onclick="calX()">Fatto: stretto di 1/8</button>');return}
 if(S.step==3){var o=avg('c',5)-d.center,e=eighths(o);
  if(Math.abs(o)<=TOLX){if(!S.okSince)S.okSince=Date.now();var t=(Date.now()-S.okSince)/1000;
   say('ok','&#10004; Centrato lungo la fila ('+(o>=0?'+':'')+o.toFixed(1)+' px)','Resta fermo '+Math.max(0,3-t).toFixed(0)+' s...',t>=3?'<button onclick="if(Math.abs(avg(\'c\',8)-S.last.center)<=TOLX)startY()">Avanti: di traverso</button>':'');return}
  S.okSince=0;var tighten=(o*S.sx)<0;   // sx = verso dello spostamento del baricentro stringendo
  say('', '<span class="arrow">'+(tighten?'&#8635;':'&#8634;')+'</span>Grano FRONTALE: '+(tighten?'STRINGI (orario)':'ALLENTA (antiorario)')+' di circa '+frac(e),
   'Il fascio e spostato di '+Math.abs(o).toFixed(1)+' pixel ('+Math.abs(o*d.pxmm).toFixed(2)+' mm) verso '+(o>0?'i pixel alti':'i pixel bassi')+'. Gira poco alla volta e aspetta 2 s: le istruzioni si aggiornano da sole.',
   '<button class="sec" onclick="go(2)">Rifai la prova del verso</button>');return}
 if(S.step==4){yLogic(d);return}
 if(S.step==5){var c=avg('c',8),m=avg('mean',8);if(!S.stab0)S.stab0={t:Date.now(),c:c,m:m};var t=(Date.now()-S.stab0.t)/1000,dc=c-S.stab0.c,dm=100*(m-S.stab0.m)/S.stab0.m;
  var ok=Math.abs(dc)<=1&&Math.abs(dm)<=3&&Math.abs(c-d.center)<=TOLX;
  say(ok&&t>=120?'ok':(ok?'':'warn'),ok?(t>=120?'&#10004; PRONTO PER LA RESINA':'Controllo di stabilita: non toccare nulla ('+(120-t).toFixed(0)+' s)'):'Si e spostato: ricontrolla',
   'Deriva baricentro '+(dc>=0?'+':'')+dc.toFixed(2)+' px, segnale '+(dm>=0?'+':'')+dm.toFixed(1)+' %. Dopo la resina (24 h) riapri questa pagina: se il fascio e ancora centrato esegui <b>gauge_dark</b> e <b>gauge_ref</b>.',
   '<button class="sec" onclick="S.stab0=null">Ricomincia il controllo</button><button class="sec" onclick="go(3)">Torna alla fila</button>');}
}
async function calX(){say('','Misuro... non toccare','');
 // la posizione "prima" e quella mediata appena prima del pulsante, la "dopo" dopo l assestamento
 var before=avg('c',8);var r=await settle();var dl=r.c-before;
 if(Math.abs(dl)<0.8){say('warn','Il fascio non si e mosso','Il grano forse non tocca ancora il laser: stringi un altro ottavo e riprova.','<button onclick="calX()">Fatto: stretto di un altro 1/8</button>');return}
 S.sx=dl>0?1:-1;S.sens=Math.abs(dl);localStorage.setItem('al_sx',S.sx);localStorage.setItem('al_sens',S.sens);go(3)}
// ---- di traverso: ricerca dei due punti all 80% del massimo, poi meta' strada
function startY(){go(4);S.phase=1;S.pos=0;S.ipmax=0;S.A=null;S.B=null;S.ymax=avg('mean',8)}
async function ystep(dir){var r=await settle();S.pos+=dir;if(r.m>S.ymax){S.ymax=r.m;S.ipmax=S.pos}
 var rel=r.m/S.ymax;
 if(S.phase==1&&rel<0.8&&S.pos>S.ipmax){S.A=S.pos;S.phase=2}
 else if(S.phase==2&&rel<0.8&&S.pos<S.ipmax){S.B=S.pos;S.phase=3}
 S.lastRel=rel;S.busy=false;logic(S.last,0)}
async function yDone(){say('','Misuro... non toccare','');var r=await settle();S.pos=(S.A+S.B)/2;S.yrel=r.m/S.ymax;S.phase=4;logic(S.last,0)}
function yLogic(d){var rel=S.ymax?avg('mean',5)/S.ymax:1;
 var info='Segnale: <b>'+(100*rel).toFixed(0)+'%</b> del massimo trovato. Passi contati: '+S.pos+' (1 passo = 1/16 di giro). ';
 if(S.phase==1)say('','<span class="arrow">&#8635;</span>Grano LATERALE: gira in senso ORARIO di 1/16 di giro, poi premi "Passo fatto"',info+'Continua finche ti dico di cambiare verso (il segnale deve prima salire, poi scendere sotto l 80%).','<button onclick="ystep(+1)">Passo fatto (orario 1/16)</button>');
 else if(S.phase==2)say('','<span class="arrow">&#8634;</span>Grano LATERALE: ora gira in senso ANTIORARIO di 1/16 di giro alla volta',info+'Primo bordo trovato al passo '+S.A+'. Continua in senso antiorario finche il segnale riscende sotto l 80% dall altra parte.','<button onclick="ystep(-1)">Passo fatto (antiorario 1/16)</button>');
 else if(S.phase==3){var tgt=(S.A+S.B)/2,n=Math.round((tgt-S.pos)*2)/2;
  if(Math.abs(tgt-S.pos)<0.6){S.phase=4;logic(d,0);return}
  say('','<span class="arrow">&#8635;</span>Grano LATERALE: gira in senso ORARIO di '+n+' sedicesimi di giro ('+(n/16).toFixed(2)+' giri)',
   'Bordi all 80% trovati ai passi '+S.B+' e '+S.A+': il centro e a meta strada ('+tgt.toFixed(1)+').','<button onclick="yDone()">Fatto</button>')}
 else{rel=S.yrel||rel;var ok=rel>=0.95;say(ok?'ok':'warn',ok?'&#10004; Centrato di traverso ('+(100*rel).toFixed(0)+'%)':'Il segnale e solo al '+(100*rel).toFixed(0)+'%: rifai la ricerca',
   'Ora ricontrolla la posizione lungo la fila (il grano laterale puo averla spostata un poco).',
   ok?'<button onclick="go(3)">Ricontrolla lungo la fila</button><button onclick="go(5)">Avanti: stabilita</button>':'<button onclick="startY()">Rifai la ricerca di traverso</button>')}}
function poll(){fetch('/align.json').then(function(r){return r.json()}).then(onData).catch(function(){$('st').textContent='nessuna risposta dal master'}).then(function(){setTimeout(poll,250)})}
steps();poll();
</script></body></html>)HTML";

void gaugeAlignHttpSetup() {
  server.on("/align", HTTP_GET, []() { gAlLastHttpMs = millis(); server.send(200, "text/html", String(GAUGE_ALIGN_HTML)); });
  server.on("/align.json", HTTP_GET, []() { gaugeAlignJson(); });
}
