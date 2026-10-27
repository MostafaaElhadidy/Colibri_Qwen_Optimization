/* slot arena microbenchmark: repack cost on first fill vs reuse, 4K vs THP */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <omp.h>
#include "expert_ffn.h"
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec*1e3+t.tv_nsec/1e6;}
static long flt(void){struct rusage r;getrusage(RUSAGE_THREAD,&r);return r.ru_minflt;}
int main(int argc,char**argv){
    int nslots=argc>1?atoi(argv[1]):1536, huge=argc>2?atoi(argv[2]):0, nmiss=argc>3?atoi(argv[3]):3000;
    const int D=2048,F=768; size_t w=(size_t)3*F*D/2;
    uint8_t **slot=malloc(sizeof(*slot)*nslots);
    if(huge){ size_t tot=w*nslots; uint8_t *a=mmap(NULL,tot,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
        madvise(a,tot,MADV_HUGEPAGE); for(int i=0;i<nslots;i++) slot[i]=a+w*i; }
    else for(int i=0;i<nslots;i++) slot[i]=malloc(w);
    uint8_t *raw=malloc(w); for(size_t i=0;i<w;i++) raw[i]=(uint8_t)(i*2654435761u>>13);
    double t0=now(); long f0=flt();
    for(int i=0;i<nslots;i++){ int64_t gp=(int64_t)F*D/2;
        xf_repack_pairs_signed(slot[i],raw,F,D); xf_repack_pairs_signed(slot[i]+gp,raw+gp,F,D); xf_repack_pairs_signed(slot[i]+2*gp,raw+2*gp,D,F);}
    double t1=now(); long f1=flt();
    printf("first fill: %.3f ms/slot, %.1f faults/slot\n",(t1-t0)/nslots,(double)(f1-f0)/nslots);
    int T=argc>4?atoi(argv[4]):1; double sum=0, worst=0;
    #pragma omp parallel num_threads(T) reduction(+:sum) reduction(max:worst)
    { unsigned r=12345+omp_get_thread_num()*7919; uint8_t *rw=malloc(w); memcpy(rw,raw,w);
      for(int k=0;k<nmiss/T;k++){ r^=r<<13;r^=r>>17;r^=r<<5; int i=(r%(nslots/T))*T+omp_get_thread_num(); int64_t gp=(int64_t)F*D/2;
        for(size_t j=0;j<w;j+=64) rw[j]^=1;
        double a=now();
        xf_repack_pairs_signed(slot[i],rw,F,D); xf_repack_pairs_signed(slot[i]+gp,rw+gp,F,D); xf_repack_pairs_signed(slot[i]+2*gp,rw+2*gp,D,F);
        double b=now()-a; sum+=b; if(b>worst)worst=b; } }
    printf("reuse x%d threads: %.3f ms/slot mean, worst %.2f ms\n",T,sum/(nmiss/T*T),worst);
    FILE *f=fopen("/proc/self/smaps_rollup","r"); char ln[256]; while(f&&fgets(ln,256,f)) if(strstr(ln,"AnonHuge")) fputs(ln,stdout);
    return 0;
}
