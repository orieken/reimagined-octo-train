from datetime import datetime

from pydantic import BaseModel, Field
from typing import Optional, Dict


class ReportMetadata(BaseModel):
    project: str
    test_run_id: str
    timestamp: datetime
    runner: str
    environment: Optional[str] = None
    branch: Optional[str] = None
    commit: Optional[str] = None
    extra: Optional[Dict[str, str]] = None
    project_id: Optional[str] = None