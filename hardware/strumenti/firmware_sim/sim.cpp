#include <random>
#include <vector>
#include <cstdio>
#include "stub/Preferences.h"
#include "stub/WebServer.h"
#include "stub/WebSocketsServer.h"
HardwareSerial Serial; EspClass ESP;
#define GAUGE_SI_PIN 26
#define GAUGE_CLK_PIN 27
#define GAUGE_AO_PIN 34
#define GAUGE_LASER_PIN 25
#define FIRMWARE_VERSION "sim"
WebServer server(80); WebSocketsServer webSocket(81);
// ---- simulatore TSL1401 + fascio
static double cableD=0, cableC=0, gainLaser=1.0, ambient=30; static int idx=-1; static bool laser=false; static double integ[128]; static double hold[128];
static double tExpose=0; std::mt19937 rng(1); std::normal_distribution<double> nz(0,6.0);  // rumore ADC 6 mV rms
static double beam(double x){ return 2000.0*exp(-x*x/(2*3.2*3.2)); }      // fascio gaussiano sigma 3.2 mm (picco 2000 mV a 20us)
static double trans(double x){ // trasmissione con ombra di diametro cableD (bordi ammorbiditi ~ diffrazione: erf 25 um)
  if(cableD<=0) return 1; double a=(x-(cableC-cableD/2))/0.025, b=((cableC+cableD/2)-x)/0.025;
  return 1-0.25*(1+erf(a))*(1+erf(b)); }
void delayMicroseconds(uint32_t us){ if(laser) tExpose+=us; }
static int lastClk=0;
void digitalWrite(int p,int v){
  if(p==GAUGE_LASER_PIN){ laser=v; return; }
  if(p==GAUGE_SI_PIN && v==1){ // fine integrazione: trasferisce cariche
    for(int i=0;i<128;i++){ double x=(i-63.5)*0.0635; double s=0; int sub=16; for(int k=0;k<sub;k++){ double xx=x+(k+0.5-sub/2.0)/sub*0.0635; s+=beam(xx)*trans(xx);} s/=sub;
      hold[i]=ambient + s*gainLaser*tExpose/20.0; }
    tExpose=0; idx=0; return; }
  if(p==GAUGE_CLK_PIN){ if(lastClk==1 && v==0) idx++; lastClk=v; }
}
uint32_t analogReadMilliVolts(int){ double v=(idx>=0&&idx<128)?hold[idx]:0; v+=nz(rng); if(v<0)v=0; if(v>3100)v=3100; return (uint32_t)v; }
#include "gauge_v06.inc"
int main(){
  // buio e riferimento senza cavo
  cableD=0; gServeRequest(GREQ_DARK); puts(gReqMsg); gServeRequest(GREQ_REF); puts(gReqMsg);
  double D[]={0.5,1.0,1.5,2.0,2.5,3.0};
  for(double d: D){ for(double c: {-0.5,0.0,0.6}){ cableD=d; cableC=c; gainLaser=1.0;
      double s=0,s2=0; int n=0; float dm,cm; for(int k=0;k<30;k++) if(gaugeMeasureRaw(8,dm,cm)){s+=dm;s2+=dm*dm;n++;}
      double m=s/n, sd=sqrt(s2/n-m*m);
      printf("D %.2f c %+.1f: area %.4f (err %+.1f um, sd %.2f um) edge %.4f center %+.3f k %.3f flat %.2f%%\n",d,c,m,1000*(m-d),1000*sd,gDiagTmp.diamEdge,gDiagTmp.center,gDiagTmp.k,gDiagTmp.flat);}}
  // energia laser -10%: k deve correggere
  cableD=2.0; cableC=0; gainLaser=0.9; float dm,cm; gaugeMeasureRaw(8,dm,cm); printf("laser -10%%: %.4f (err %+.1f um) k %.3f\n",dm,1000*(dm-2.0),gDiagTmp.k);
  cableD=0; gainLaser=1; gaugeMeasureRaw(8,dm,cm); printf("senza cavo: ok=%d why=%s\n",gDiagTmp.ok,gDiagTmp.why);
  cableD=2.0; cableC=0; for(int i=0;i<4;i++){bool ok=gaugeMeasureRaw(8,dm,cm); printf("pre %d %s %.4f\n",ok,gDiagTmp.why,dm);}
  gReqArg=50; gServeRequest(GREQ_STAT); puts(gReqMsg);
}
