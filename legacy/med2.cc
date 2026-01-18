#include <iostream>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include <fstream>

using namespace std;

int compar(const void *x,const void *y)
{
    double* a=(double*)x, *b=(double*)y;
    return (*a)>(*b)?1:((*a)<(*b)?-1:0);
}

double median(double* x,int k)
{
   int n=2*k+1;
   double y[n];
   for(int i=0;i<n;i++) y[i]=x[i];
   qsort(y,n,sizeof(double),compar); 
   return y[k];
}

void filter(int n,double* x,double *y,int k)
{
    	for(int i=0;i<k;i++) y[i]=x[i];
	    for(int i=k;i<n-k;i++) y[i]=median(x+i-k,k);
	    for(int i=n-k;i<n;i++) y[i]=x[i];
}

void wavelet(int n,double* x,double *y,int k)
{
	for(int i=0;i<n;i++)
	{
		y[i]=0;
		double cnt=0;
		for(int j=i-2*k;j<=i+2*k;j++) if(j>=0 && j<n)
		{
			double t2=double(i-j)/k; t2*=t2;
			double w=(1-t2)*exp(-t2/2);
			y[i]+=x[j]*w;
			cnt+=w;
		}
		y[i]/=cnt;
	}
}

const int nmax=1000000;


void norm(double* x, int n, int w)
{
}

int main(int argc,char** argv)
{
    int kkk=5;
    int w=nmax;
    double q=0;
    double tt=2;
    int skip=0;
//	int np=100;
    int pk=10;
    int fl_vc=0;
    double S=0;
    int www=nmax;
    for(int i=1;i<argc;i++)
    {
    	if(strcmp(argv[i],"-f")==0) kkk=atoi(argv[++i]);
    	else if(strcmp(argv[i],"-l")==0) w=atoi(argv[++i]);
    	else if(strcmp(argv[i],"-q")==0) q=atof(argv[++i]);
    	else if(strcmp(argv[i],"-p")==0) tt=atof(argv[++i]);
    	else if(strcmp(argv[i],"-x")==0) skip=atoi(argv[++i]);
//    	else if(strcmp(argv[i],"-h")==0) np=atoi(argv[++i]);
    	else if(strcmp(argv[i],"-k")==0) pk=atoi(argv[++i]);
    	else if(strcmp(argv[i],"-W")==0) www=atoi(argv[++i]);
    	else if(strcmp(argv[i],"-s")==0) S=atof(argv[++i]);
    	else if(strcmp(argv[i],"-vc")==0) fl_vc=1;
    	else return 1;
    }
    const int c=2, np=1000;
    double* x[c],*t=new double [nmax],*p=new double [nmax],*pp=new double [nmax],*f=new double [nmax];
    for(int j=0;j<c;j++) x[j]=new double [nmax];
	for(int i=0;i<skip && cin.good();i++) { cin>>t[0]; for(int j=0;j<c;j++) cin>>x[j][0]; cin>>p[0]; }
    int n;
    for(n=0;n<nmax && n<w && cin.good();n++) { cin>>t[n]; for(int j=0;j<c;j++) cin>>x[j][n]; cin>>p[n]; }
    n--;
    double* y[c],*z[c];
    for(int j=0;j<c;j++) { y[j]=new double [n]; z[j]=new double [n]; }
    for(int j=0;j<c;j++)
    {
    	filter(n,x[j],y[j],kkk);
//    	filter(n,x[j],z[j],w);
	}
	if(S!=0) 
	{
//		ofstream qqq("qqq");
		for(int i=0;i<n;i++) pp[i]=p[i];
		for(int i=0;i<n;i++)
		{
			double ya=0,y2=0,pa=0,p2=0;
			int cnt=0,ind=fl_vc?0:1;
			for(int j=i-www;j<i+www;j++) if(j>=0 && j<n) 
			{ 
				ya+=y[ind][j]; y2+=y[ind][j]*y[ind][j]; 
				pa+=pp[j]; p2+=pp[j]*pp[j];
				cnt++; 
			}
			ya/=cnt; y2=sqrt(y2/cnt-ya*ya);
			pa/=cnt; p2=sqrt(p2/cnt-pa*pa);
//			qqq<<((pp[i]-pa)/p2)<<'\t'<<((y[ind][i]-ya)/y2)<<endl;
//			qqq<<((pp[i]))<<'\t'<<((y[ind][i]-ya)/y2)<<'\t'<<pa<<endl;
			p[i]=(pp[i]-pa)/p2+S*(y[ind][i]-ya)/y2;
		}
	}
   	filter(n,p,pp,pk);
//   	wavelet(n,p,pp,pk);
   	
   	if(q<=0)
   	{
   		double p2=0;
   		for(int i=0;i<n;i++) p2+=pp[i]*pp[i];
   		q=2*sqrt(p2/n);
   	}
   	
	double T=0,Ta=0,T2=0;
	int cnt=0;
	int ipre=0;
	for(int i=0;i<n;i++) f[i]=-1;
	for(int i=kkk;i<n-kkk;i++)
	{
		if(pp[i-1]<q && pp[i]>=q)
		{
			if(ipre && t[i]-t[ipre]>tt)
			{
				T=t[i]-t[ipre]; Ta+=T; T2+=T*T; cnt++;
//				double TI=1;
				for(int j=ipre;j<i;j++)
				{
//                    if(t[j]-t[ipre]<2*TI)  f[j]=(t[j]-t[ipre])/TI/4;
//                    else if(t[i]-t[j]<TI) f[j]=(t[j]-t[i])/TI/4+1;
//					else f[j]=.5+.25*(t[j]-t[ipre]-2*TI)/(T-3*TI);
					f[j]=(t[j]-t[ipre])/T;
				}
			}
			if(!ipre || t[i]-t[ipre]>tt) ipre=i;
		}
	}
	
	double X[c][c][np]={},M[c][np]={};
	int nnn[np]={};
	for(int i=0;i<n;i++) if(f[i]>=0)
	{
		int l=floor(f[i]*np); if(l==np) l--;
		for(int k=0;k<c;k++) 
		{
			M[k][l]+=y[k][i];
			for(int j=0;j<c;j++) X[k][j][l]+=y[k][i]*y[j][i];
		}
		nnn[l]++;
	}
	for(int l=0;l<np;l++) 
	{
		for(int k=0;k<c;k++) 
		{
			M[k][l]/=nnn[l];
			for(int j=0;j<c;j++) X[k][j][l]/=nnn[l];
		}
		double cov=(X[0][1][l]-M[0][l]*M[1][l]);
		double var1=(X[1][1][l]-M[1][l]*M[1][l]);
		double a=cov/var1;
		double b=M[0][l]-a*M[1][l];
		double var0=(X[0][0][l]-M[0][l]*M[0][l]);
		double err=sqrt((var0/var1-a*a));
		double aa=cov/var0;
		double bb=M[1][l]-aa*M[0][l];
		double erer=sqrt((var1/var0-aa*aa));
		if(fl_vc) cerr<<a<<'\t'<<b<<'\t'<<err<<'\t'<<nnn[l]<<endl;
		else cerr<<(1/aa)<<'\t'<<(-bb/aa)<<'\t'<<(erer/aa/aa)<<'\t'<<nnn[l]<<endl;
	}
	
	
    for(int i=kkk;i<n-kkk;i++)
    {
    	cout<<t[i]<<'\t';
    	cout<<pp[i]<<'\t'<<f[i]<<'\t'<<y[0][i]<<'\t'<<y[1][i]<<endl; 
    }
    for(int j=0;j<c;j++) delete z[j];
    for(int j=0;j<c;j++) delete y[j];
    for(int j=0;j<c;j++) delete x[j];

    Ta/=cnt; T2/=cnt;
    double dT=sqrt(T2-Ta*Ta);
    ofstream("par")<<"Ta="<<Ta<<endl<<"dTa="<<dT<<endl<<"q="<<q<<endl;
    return 0;
}

