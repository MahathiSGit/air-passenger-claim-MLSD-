"""LangGraph ReAct-style researcher; re-plans after reading each tool result."""
from __future__ import annotations
import json,time
from typing import Any,TypedDict
from .tools import langchain_tools
class AgentState(TypedDict,total=False):
    claim:dict[str,Any]
    passages:list[dict[str,Any]]
    calls:list[dict[str,Any]]
    tool_call_count:int
    next_tool:dict[str,str]
    done:bool
class LangGraphResearchAgent:
    """Selects one LangChain tool at a time and re-plans from retrieved evidence."""
    ALLOWED={"corpus_search","clause_lookup","claim_field_lookup"}
    def __init__(self,model,max_tool_calls:int=6,tool_timeout_seconds:float=10):
        if not 1<=max_tool_calls<=6:raise ValueError("max_tool_calls must be 1..6")
        self.model,self.max_tool_calls,self.tool_timeout_seconds=model,max_tool_calls,tool_timeout_seconds
    def run(self,claim:dict[str,Any]):
        from langgraph.graph import END,StateGraph
        from concurrent.futures import ThreadPoolExecutor,TimeoutError as FutureTimeout
        tools=langchain_tools()
        def select(state:AgentState):
            remaining=self.max_tool_calls-state["tool_call_count"]
            answer=self.model.generate_json(task="research_tool_selection",payload={
                "claim":state["claim"],"retrieved_passages":[{"citation":p.get("citation"),"text":str(p.get("text",""))[:1800]} for p in state["passages"][-8:]],
                "previous_tool_calls":state["calls"],"tool_call_budget_remaining":remaining,
                "available_tools":[{"name":"corpus_search","purpose":"search natural-language query"},{"name":"clause_lookup","purpose":"lookup a clause and linked conditions"},{"name":"claim_field_lookup","purpose":"read one validated claim field"}],
                "instruction":"Choose exactly one next tool call based on the claim and what retrieved passages say, or return {action:'finish'} only when all modifying conditions/exemptions and linked facilities have been checked. Derive a follow-up query from retrieved text when it points to a related clause. Return {action:'tool',tool,argument} or {action:'finish'}. Do not decide eligibility."})
            if answer.get("action")=="finish":return {"done":True}
            tool=answer.get("tool"); arg=str(answer.get("argument",""))[:500]
            if tool not in self.ALLOWED or not arg:
                if state["tool_call_count"]==0:return {"next_tool":{"tool":"corpus_search","argument":str(state["claim"].get("complaint",""))},"done":False}
                return {"done":True}
            return {"next_tool":{"tool":tool,"argument":arg},"done":False}
        def invoke(state:AgentState):
            item=state["next_tool"]; tool=item["tool"]; arg=item["argument"]; started=time.perf_counter()
            try:
                def call():
                    if tool=="corpus_search":return tools[tool].invoke({"query":arg,"top_k":5})
                    if tool=="clause_lookup":return tools[tool].invoke({"clause_id":arg,"top_k":5})
                    return tools[tool].invoke({"claim":state["claim"],"field":arg})
                pool=ThreadPoolExecutor(max_workers=1); future=pool.submit(call)
                try: output=future.result(timeout=self.tool_timeout_seconds)
                finally: pool.shutdown(wait=False,cancel_futures=True)
                passages=output if tool!="claim_field_lookup" and isinstance(output,list) else []
                record={"tool":tool,"query_or_field":arg,"result_count":len(passages),"latency_seconds":round(time.perf_counter()-started,4),"status":"ok"}
            except FutureTimeout:
                passages=[]; record={"tool":tool,"query_or_field":arg,"latency_seconds":round(time.perf_counter()-started,4),"status":"timeout"}
            except Exception as exc:
                passages=[]; record={"tool":tool,"query_or_field":arg,"latency_seconds":round(time.perf_counter()-started,4),"status":"error","error_type":type(exc).__name__}
            return {"passages":state["passages"]+passages,"calls":state["calls"]+[record],"tool_call_count":state["tool_call_count"]+1}
        def route(state:AgentState):return END if state.get("done") or state["tool_call_count"]>=self.max_tool_calls else "invoke_tool"
        graph=StateGraph(AgentState); graph.add_node("select_tool",select); graph.add_node("invoke_tool",invoke)
        graph.set_entry_point("select_tool"); graph.add_conditional_edges("select_tool",route,{"invoke_tool":"invoke_tool",END:END}); graph.add_edge("invoke_tool","select_tool")
        end=graph.compile().invoke({"claim":claim,"passages":[],"calls":[],"tool_call_count":0,"done":False},config={"recursion_limit":3*self.max_tool_calls+5})
        unique={(str(p.get("citation","")),str(p.get("text",""))):p for p in end["passages"]}
        return {"passages":list(unique.values()),"calls":end["calls"]}

