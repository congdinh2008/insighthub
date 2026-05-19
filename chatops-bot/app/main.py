"""DO2603 Day 5 skeleton. No Slack event is accepted before auth is implemented."""
from fastapi import FastAPI, HTTPException
app = FastAPI(title="InsightHub ChatOps skeleton", version="0.2.0")

@app.get("/healthz")
def health():
    return {"status": "skeleton", "ready": False, "transport": "not_configured"}

@app.post("/slack/events")
def slack_events():
    # Do not echo URL challenges or log event bodies before authentication.
    raise HTTPException(status_code=501, detail="Implement and test the selected Slack adapter first")

async def handle_question(question: str) -> str:
    # Day 5: transport -> deduplicated queue -> bounded read-only tool -> audit.
    # Mutation requires a separate identity and approval bound to exact action.
    raise NotImplementedError("Day 5 learner implementation")
