from pydantic import BaseModel, Field
from typing import List, Optional, Any


class TopicMetadata(BaseModel):
    """Metadata for a lesson topic."""
    topicId: str
    title: str
    duration: str
    lessonContent: Optional[dict] = None


class LessonResponse(BaseModel):
    """Single lesson/subject in the catalogue."""
    subject: str
    subjectId: str
    descriptor: str
    topics: List[TopicMetadata]


class LessonsListResponse(BaseModel):
    """Response model for lessons catalogue."""
    lessons: List[LessonResponse]
    total_count: int = Field(description="Total number of lessons returned")
