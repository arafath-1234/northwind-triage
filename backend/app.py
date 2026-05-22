"""
Northwind Triage — FastAPI Backend
Run with: uvicorn app:app --reload
or: python app.py
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn

load_dotenv()

from agent import triage_message

app = FastAPI(title="Northwind Triage API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


class TriageRequest(BaseModel):
    message: str
    sender_name: str | None = None
    channel: str | None = "webform"
    subject: str | None = None


class TriageResponse(BaseModel):
    category: str
    priority: str
    route_to: str
    needs_human_review: bool
    draft_reply: str
    reasoning: str


@app.post("/triage", response_model=TriageResponse)
def triage(req: TriageRequest):
    """
    Accept a raw customer message and return a structured triage decision.
    """
    try:
        msg_dict = {
            "id": "live",
            "channel": req.channel or "webform",
            "received_at": "now",
            "sender_name": req.sender_name or "Unknown",
            "subject": req.subject,
            "body": req.message,
        }
        result = triage_message(msg_dict)
        return TriageResponse(**{k: result[k] for k in TriageResponse.model_fields})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)