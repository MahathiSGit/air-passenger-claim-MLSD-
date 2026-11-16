"""Run prompt variants against the fixed scenario corpus and report four transparent metrics."""
from __future__ import annotations
import argparse,json,os,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from app.config import settings
from app.services.workflow_adapter import run_claim_workflow
STOP={"the","and","for","with","from","that","this","were","was","are","has","have","into","when","under","shall","would","could","there","their","they","only","not","due","claim","flight","passenger","airline","paragraph","provide","provided","provision","result","recommendation","human","review","demo","mode","output","evidence"}
def words(text):return {w for w in re.findall(r"[a-z0-9%.-]+",text.lower()) if len(w)>2 and w not in STOP}
def score(scenario,result):
    passages=result.get("regulation_research",{}).get("relevant_provisions",[])
    contexts=[str(p.get("text","")) for p in passages]
    expected=scenario["expected_outcome"]
    actual=result.get("entitlement",{}).get("recommendation","")
    facts=scenario["required_facts"]
    joined=" ".join(contexts).lower()
    grounded=sum(1 for fact in facts if fact.lower() in joined)/max(len(facts),1)
    relevant=[p for p in contexts if len(words(p)&words(" ".join(facts)))>0]
    context_relevance=len(relevant)/max(len(contexts),1)
    rationale=str(result.get("entitlement",{}).get("rationale",""))
    rationale_lower=rationale.lower()
    faithful=(sum(1 for fact in facts if fact.lower() in (rationale_lower+" "+joined))/max(len(facts),1))
    if actual==expected:faithful=min(1.0,faithful+0.25)
    sentences=[s.strip() for s in re.split(r"[.!?]+",rationale) if s.strip()]
    unsupported=sum(1 for s in sentences if not words(s)&words(" ".join(contexts)))/max(len(sentences),1)
    unresolved=[c for c in result.get("entitlement",{}).get("citations",[]) if not any(c==p.get("citation") for p in passages)]
    hallucination=min(1.0,unsupported+(len(unresolved)/max(len(result.get("entitlement",{}).get("citations",[])),1)))
    return {"groundedness":round(grounded,4),"context_relevance":round(context_relevance,4),"faithfulness":round(faithful,4),"hallucination_rate":round(hallucination,4),"route_correct":actual==expected}
def mean_rows(rows):
    keys=("groundedness","context_relevance","faithfulness","hallucination_rate")
    return {k:round(sum(r[k] for r in rows)/max(len(rows),1),4) for k in keys}
def run_variant(scenarios,version,mode):
    os.environ["PROMPT_VERSION"]=version; object.__setattr__(settings,"agent_mode",mode)
    rows=[]; failures=[]
    for scenario in scenarios:
        try:
            result=run_claim_workflow(scenario["claim"])
            scores=score(scenario,result)
            rows.append({"scenario_id":scenario["id"],**scores,"route":result.get("entitlement",{}).get("recommendation"),"prompt_version":result.get("prompt_version"),"cost":result.get("per_run_cost",0),"model_calls":result.get("model_calls",[])})
        except Exception as exc: failures.append({"scenario_id":scenario["id"],"error_type":type(exc).__name__})
    return {"prompt_version":version,"scenario_count":len(scenarios),"successful_runs":len(rows),"failures":failures,"metrics":mean_rows(rows),"route_accuracy":round(sum(r["route_correct"] for r in rows)/max(len(rows),1),4),"per_scenario":rows,"cost_per_100_runs":round(sum(r["cost"] for r in rows)/max(len(rows),1)*100,6),"largest_single_cost_driver":max((c for r in rows for c in r.get("model_calls",[])),key=lambda c:float(c.get("cost",0)),default=None)}
def main():
    p=argparse.ArgumentParser(); p.add_argument("--dataset",default=str(Path(__file__).with_name("scenarios.json"))); p.add_argument("--output",default="eval/report.json"); p.add_argument("--mode",choices=["demo","llm"],default="llm"); p.add_argument("--before",default="v1"); p.add_argument("--after",default="v2"); args=p.parse_args()
    scenarios=json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    if len(scenarios)<20:raise SystemExit("Evaluation set must contain at least 20 scenarios")
    before=run_variant(scenarios,args.before,args.mode); after=run_variant(scenarios,args.after,args.mode)
    report={"evaluation":"fixed scenario batch","mode":args.mode,"metric_computation":{"groundedness":"fraction of required evidence facts present in retrieved passages","context_relevance":"fraction of retrieved passages overlapping required evidence terms","faithfulness":"required evidence facts reflected by rationale/evidence, with route match bonus","hallucination_rate":"unsupported rationale sentence fraction plus unresolved-citation fraction"},"before":before,"after":after,"metric_delta_after_minus_before":{k:round(after["metrics"][k]-before["metrics"][k],4) for k in before["metrics"]},"deliberate_change":"v1 to v2 adds an explicit search for linked conditions, exceptions and facilities before concluding.","prompt_comparison":{"same_scenarios":len(scenarios),"metric_winners":{k:{"better":"after" if (after["metrics"][k]>before["metrics"][k] if k!="hallucination_rate" else after["metrics"][k]<before["metrics"][k]) else "before" if (before["metrics"][k]>after["metrics"][k] if k!="hallucination_rate" else before["metrics"][k]<after["metrics"][k]) else "tie","absolute_delta":round(after["metrics"][k]-before["metrics"][k],4)} for k in before["metrics"]}}}
    Path(args.output).parent.mkdir(parents=True,exist_ok=True); Path(args.output).write_text(json.dumps(report,indent=2),encoding="utf-8"); print(json.dumps({"report":args.output,"before":before["metrics"],"after":after["metrics"],"delta":report["metric_delta_after_minus_before"]},indent=2))
if __name__=="__main__":main()

