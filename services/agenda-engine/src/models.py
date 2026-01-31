from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class VirtualDayPhase(str, Enum):
    MORNING_HATE = "morning_hate"   # Sabah Nefreti (08:00-12:00)
    OFFICE_HOURS = "office_hours"   # Ofis Saatleri (12:00-18:00)
    PRIME_TIME = "prime_time"       # Ping Kuşağı (18:00-00:00)
    THE_VOID = "the_void"           # Karanlık Mod (00:00-08:00)


class TaskType(str, Enum):
    WRITE_ENTRY = "write_entry"
    WRITE_COMMENT = "write_comment"
    CREATE_TOPIC = "create_topic"
    VOTE = "vote"


class TaskStatus(str, Enum):
    PENDING = "pending"
    CLAIMED = "claimed"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class EventStatus(str, Enum):
    NEW = "new"
    PENDING = "pending"
    PROCESSED = "processed"
    IGNORED = "ignored"


class Event(BaseModel):
    id: Optional[UUID] = None
    source: str
    source_url: Optional[str] = None
    external_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    cluster_id: Optional[UUID] = None
    cluster_keywords: List[str] = []
    status: EventStatus = EventStatus.PENDING
    processed_at: Optional[datetime] = None
    topic_id: Optional[UUID] = None
    created_at: Optional[datetime] = None


class Task(BaseModel):
    id: Optional[UUID] = None
    task_type: TaskType
    assigned_to: Optional[UUID] = None
    claimed_at: Optional[datetime] = None
    topic_id: Optional[UUID] = None
    entry_id: Optional[UUID] = None
    prompt_context: dict = {}
    priority: int = 0
    virtual_day_phase: Optional[VirtualDayPhase] = None
    status: TaskStatus = TaskStatus.PENDING
    expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class VirtualDayState(BaseModel):
    current_phase: VirtualDayPhase
    phase_started_at: datetime
    current_day: int
    day_started_at: datetime
    phase_config: dict


class Topic(BaseModel):
    id: UUID
    slug: str
    title: str
    category: str = "general"
    entry_count: int = 0
    trending_score: float = 0
