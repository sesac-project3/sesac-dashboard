from pydantic import BaseModel


class TranscribeResponse(BaseModel):
    fileName: str
    transcript: str
    aiInsightSummary1: str
    aiInsightSummary2: str
    aiInsightSummary3: str
