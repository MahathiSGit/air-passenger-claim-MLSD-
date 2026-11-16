"""End-to-end Locust transaction: submit, poll, record final run latency."""
from locust import HttpUser,task,between,events
import time,uuid
class ClaimUser(HttpUser):
    wait_time=between(0.1,0.5)
    def on_start(self):
        self.client_id=str(uuid.uuid4())
    @task
    def complete_claim(self):
        claim={"complaint":"My flight was cancelled. I was at the airport and took an alternate flight four hours later.","disruption_type":"cancellation"}
        headers={"X-Client-ID":self.client_id,"X-Request-ID":str(uuid.uuid4())}
        started=time.perf_counter(); run_id=None; failure=None
        try:
            response=self.client.post("/api/v1/claims",json=claim,headers=headers,name="submit_claim",timeout=30)
            if response.status_code!=202:raise RuntimeError(f"submission returned {response.status_code}")
            run_id=response.json()["claim_id"]; deadline=time.perf_counter()+300
            while time.perf_counter()<deadline:
                result=self.client.get(f"/api/v1/claims/{run_id}/result",headers=headers,name="poll_result")
                if result.status_code==200:break
                if result.status_code==409:raise RuntimeError("claim worker returned failed state")
                time.sleep(0.5)
            else:raise TimeoutError("run exceeded 300 seconds")
        except Exception as exc:failure=exc
        events.request.fire(request_type="RUN",name="complete_run",response_time=(time.perf_counter()-started)*1000,response_length=0,exception=failure,context={"run_id":run_id})

