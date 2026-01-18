load 'tmp.rp'

set term pdfcairo enh size 7,5 font "Helvetica,10"
set out "linreg.pdf"

unset key

df=.001
n=25

set grid

stat "dat" u 5:4 nooutput

coef=STATS_min_y<-2?.1:1
Imax=-STATS_min_y*coef
Vmin=STATS_min_x
Vmax=STATS_max_x

set multi 

sx=.07; sy=.07;
dx=(1-sx)/5; dy=(1-sy)/5;
c=.9;
set size dx*c,dy*c

set fit quiet
set fit logfile '/dev/null'
set lmargin 0; set rmargin 0; set tmargin 0; set bmargin 0;

set format y ''
do for [k=0:n-1] {

set or sx+(k%5+1-c)*dx,sy+(4-k/5+1-c)*dy

f=1./n/2+1./n*k
unset label
if(k==n-1) {
	set label "Voltage (mV)" at screen .5,sy/2 font ",16" center
	set label "Current (nA)" at screen sx/2,.5 font ",16" rotate by 90 center
}

if(k/5==4) { set format x '%g'; set xtics scale 1 }
else { set format x ''; set xtics scale 0 }

if(k%5==0) { set format y '%g'; set ytics scale 1 }
else { set format y ''; set ytics scale 0 }

set xrange [*:*]
set yrange [*:*]

#fit a*x+b 'dat' u ($4<0?$4*coef:NaN):(abs($3-f)<df?$5:NaN) via a,b
set fit errorvariables
fit a*x+b 'dat' u ($4<0?$4*coef:NaN):(abs($3-f)<df?$5:NaN) via a,b
SSR_r=FIT_WSSR
sigma1=SSR_r/(FIT_NDF+2)
BIC1=log(FIT_NDF+2)*2+(FIT_NDF+2)*log(sigma1)

fit q*x**2+a1*x+b1 'dat' u ($4<0?$4*coef:NaN):(abs($3-f)<df?$5:NaN) via a1,b1,q
SSR_ur=FIT_WSSR
sigma2=SSR_ur/(FIT_NDF+3)
BIC2=log(FIT_NDF+3)*3+(FIT_NDF+3)*log(sigma2)

F=(SSR_r-SSR_ur)/SSR_ur*(FIT_NDF-1)

x0=(a-a1)/2/q

stat 'dat' u (abs($3-f)<df && $4<0?$4*coef:NaN) nooutput
x0=(x0>STATS_min && x0<STATS_max)?x0:STATS_min
ddd(x)=q*x**2+a1*x+b1-a*x-b
fmax(a,b)=a>b?a:b
fmin(a,b)=a<b?a:b
max(a,b,c)=a>fmax(b,c)?a:fmax(b,c)
min(a,b,c)=a<fmin(b,c)?a:fmin(b,c)
d1=max(ddd(STATS_min),ddd(STATS_max),ddd(x0))
d2=min(ddd(STATS_min),ddd(STATS_max),ddd(x0))
delta=fmax(abs(d1),abs(d2))

set label sprintf("{/Symbol f}=%g",f) at graph .02,.9 left
#set label sprintf("{/Symbol f}=%g\nF=%g\n%g\n%g\n%g",f,delta,FIT_STDFIT,x0,ddd(x0)) at graph .02,.9 left

set xrange [Vmin-10:Vmax]
set xtics 20 out nomirror
set yrange [-Imax*1.1:-.01]
ty=floor(Imax/3.*10.)/10.
set ytics ty>0?ty:.1 out nomirror


plot 'dat' u (abs($3-f)<df?$5:NaN):($4<0?$4*coef:NaN) w p pt 7  ps .5,(x-b)/a w l lw 3
#plot 'dat' u (abs($3-f)<df?$5:NaN):($4<0?$4*coef:NaN) w p pt 7  ps .5,q*x**2+a1*x+b1 w l lw 3

}
unset multi
