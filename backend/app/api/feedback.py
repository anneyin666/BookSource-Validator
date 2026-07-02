import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter()

FEEDBACK_FILE = Path(__file__).parent.parent.parent / "data" / "feedback.jsonl"


class FeedbackPayload(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    contact: Optional[str] = Field(default=None, max_length=200)
    page_url: Optional[str] = Field(default=None, max_length=1000)
    user_agent: Optional[str] = Field(default=None, max_length=1000)
    viewport: Optional[str] = Field(default=None, max_length=100)
    theme: Optional[str] = Field(default=None, max_length=20)


@router.post("/feedback")
async def submit_feedback(payload: FeedbackPayload, request: Request):
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="反馈内容不能为空")

    record = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "message": message,
        "contact": (payload.contact or "").strip(),
        "page_url": payload.page_url,
        "user_agent": payload.user_agent,
        "viewport": payload.viewport,
        "theme": payload.theme,
        "client_host": request.client.host if request.client else "",
    }

    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with FEEDBACK_FILE.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")

    return {"code": 200, "message": "反馈已保存"}
