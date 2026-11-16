"""Utilities for repeatable cold/warm cache measurements."""
import argparse,json,statistics,time
from rag.retrieval import retrieve_passages,_retrieve_cached
QUERIES=["cancellation alternate flight compensation conditions", "delay block time facilities meals refreshments", "downgrading international sector reimbursement"]
def measure(rounds:int,clear:bool):
    if clear:_retrieve_cached.cache_clear()
    samples=[]
    for _ in range(rounds):
        for q in QUERIES:
            start=time.perf_counter(); retrieve_passages(q,top_k=5); samples.append((time.perf_counter()-start)*1000)
    samples.sort(); return {"requests":len(samples),"mean_ms":statistics.mean(samples),"p50_ms":samples[len(samples)//2],"p95_ms":samples[min(len(samples)-1,int(len(samples)*.95))]}
def main():
    p=argparse.ArgumentParser();p.add_argument("--rounds",type=int,default=10);a=p.parse_args()
    cold=measure(1,True);warm=measure(a.rounds,False)
    print(json.dumps({"cold":cold,"warm":warm,"warm_p95_reduction_percent":round((cold["p95_ms"]-warm["p95_ms"])/max(cold["p95_ms"],.0001)*100,2),"provider_cost_change_per_run":0,"note":"Retrieval/embedding cache only; exact cost savings depend on observed model calls."},indent=2))
if __name__=="__main__":main()
