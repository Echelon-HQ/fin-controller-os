from pathlib import Path
from fastapi import APIRouter
from pydantic import BaseModel
from orchestration.controller_adapter import tool_run_daily_digest_impl

BASE_DIR = Path(__file__).resolve().parents[1]

CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
LOG_DIR = BASE_DIR / "log"

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    as_of_date: str


@router.post("/chat")
def chat(req: ChatRequest):
    message_lower = req.message.lower()

    if "daily" in message_lower or "today" in message_lower:
        digest = tool_run_daily_digest_impl(
            config_dir=CONFIG_DIR,
            data_dir=DATA_DIR,
            log_dir=LOG_DIR,
            as_of_date_str=req.as_of_date,
            mode="summary",
        )

        response = f"Status for {digest['date']}: {digest['status_label']}.\n"

        if digest["recommendations"]:
            response += "Top recommendations:\n"
            for rec in digest["recommendations"][:3]:
                response += f"- {rec['description']}\n"
        else:
            response += "No urgent actions today."

        return {"response": response}

    return {
        "response": "I can help with daily status, weekly summaries, or scenarios."
    }
