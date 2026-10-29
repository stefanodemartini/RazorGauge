// simulazione: fascio con inclinazioni tx (lungo la fila) e ty (di traverso); l'utente esegue le istruzioni
var els={};function el(){return {innerHTML:'',textContent:'',className:'',style:{},width:1000,height:220,getContext:function(){return new Proxy({},{get:function(){return function(){}}})}}}
global.document={getElementById:function(i){return els[i]||(els[i]=el())}};
global.localStorage={d:{},getItem:function(k){return this.d[k]||null},setItem:function(k,v){this.d[k]=v}};
var now=0;global.Date={now:function(){return now}};
var timers=[];global.setTimeout=function(f,ms){timers.push({t:now+ms,f:f})};
global.fetch=function(){return {then:function(){return {catch:function(){return {then:function(){}}}}}}};
var tx=0.9,ty=-0.6,ang=0, n=0;   // stato reale: inclinazioni in gradi; ang = rotazione ellisse
function data(){var c=63.5+(-tx)*44.9 + 0.3*Math.sin(n);  // 2.85 mm/deg / 0.0635 = 44.9 px/deg; stringere frontale -> tx diminuisce
  var m=1500*Math.exp(-2*Math.pow(ty*2.85/2.6,2))*(1+0.005*Math.sin(n*1.7));
  var p=[];for(var i=0;i<128;i++)p.push(Math.round(m*1.6*Math.exp(-2*Math.pow((i-c)/90,2))));
  return {n:++n,exp:20,peak:Math.max.apply(null,p),mean:m,c:c,center:63.5,fwhm:60+Math.round(30*Math.cos(ang)),bal:0,sat:0,lo:16,hi:111,mvsat:2450,pxmm:0.0635,p:p}}
eval(require('fs').readFileSync('al.js','utf8').replace('steps();poll();','steps();'));
function tick(ms){var end=now+ms;while(now<end){now+=250;onData(data());var due=timers.filter(function(x){return x.t<=now});timers=timers.filter(function(x){return x.t>now});due.forEach(function(x){x.f()})}}
async function run(){
 for(var it=0;it<60;it++){
  await new Promise(r=>setImmediate(r)); tick(3500); await new Promise(r=>setImmediate(r));
  var cmd=els.cmd.innerHTML.replace(/<[^>]+>/g,''), btn=els.btns.innerHTML;
  console.log('['+S.step+'/'+S.phase+'] '+cmd.slice(0,110)+' | tx='+tx.toFixed(3)+' ty='+ty.toFixed(3));
  if(/PRONTO/.test(cmd)) break;
  if(S.step==1){ang=0; go(S.sx?3:2); continue}
  if(S.step==2){tx-=1/8*0.5/14*57.3; var p=calX(); for(var k=0;k<20;k++){tick(250);await new Promise(r=>setImmediate(r))} continue}
  if(S.step==3){ if(/Centrato/.test(cmd)){tick(3500); if(Math.abs(avg('c',8)-63.5)<=TOLX){ if(S.ydone) go(5); else startY();} continue}
     var m=cmd.match(/circa (\d+) ottav/); var e=m?+m[1]:(/1\/16/.test(cmd)?0.5:0.25); var tight=/STRINGI/.test(cmd); tx+= (tight?-1:1)*e/8*0.5/14*57.3*(0.9+0.2*Math.random()); continue}
  if(S.step==4){ if(S.phase==1){ty+=1/16*0.5/14*57.3; ystep(+1); for(var k=0;k<12;k++){tick(250);await new Promise(r=>setImmediate(r))} continue}
     if(S.phase==2){ty-=1/16*0.5/14*57.3; ystep(-1); for(var k=0;k<12;k++){tick(250);await new Promise(r=>setImmediate(r))} continue}
     if(S.phase==3){var m=cmd.match(/ORARIO di ([\-\d.]+) sedicesimi/); var q=m?+m[1]:0; ty+=q/16*0.5/14*57.3; yDone(); for(var k=0;k<12;k++){tick(250);await new Promise(r=>setImmediate(r))} continue}
     if(/Centrato di traverso/.test(cmd)){S.ydone=1; go(3); continue} else {startY(); continue}}
  if(S.step==5){tick(125000);}
 }
 console.log('FINE: tx=%s° ty=%s°  -> spostamento sul chip lungo la fila %s mm, di traverso %s mm',tx.toFixed(3),ty.toFixed(3),(tx*2.85).toFixed(2),(ty*2.85).toFixed(2));
}
run();
