"""
Pydantic schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


# ============================================================================
# User Schemas
# ============================================================================

class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserResponse(UserBase):
    """Schema for user response."""
    id: UUID
    is_active: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Auth Schemas
# ============================================================================

class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""
    user_id: str
    email: str


# ============================================================================
# Video Schemas
# ============================================================================

class VideoBase(BaseModel):
    """Base video schema."""
    name: str = Field(..., min_length=1, max_length=200)


class VideoCreate(VideoBase):
    """Schema for video upload."""
    pass


class VideoUpdate(BaseModel):
    """Schema for video update."""
    name: Optional[str] = None


class TimelineEntry(BaseModel):
    """Timeline entry for video analysis."""
    timestamp: str
    what_happens: str
    emotion_shift: str
    retention_hook: str
    cta_presence: bool = False


class RecommendationEntry(BaseModel):
    """Recommendation for video improvement."""
    type: str
    suggestion: str
    expected_improvement: float = 0.0


class VideoAnalysisResult(BaseModel):
    """Analysis result from Claude Vision."""
    hook_type: str
    emotion: str
    pacing: str
    content_style: Optional[str] = None
    has_text_overlay: bool = False
    has_face: bool = False
    has_music: bool = False
    has_voiceover: bool = False
    viral_probability: float = 0.0
    predicted_engagement: float = 0.0
    confidence_score: float = 0.0
    timeline: List[TimelineEntry] = []
    recommendations: List[RecommendationEntry] = []
    reasoning: Optional[str] = None


class VideoResponse(VideoBase):
    """Schema for video response."""
    id: UUID
    user_id: UUID
    video_url: Optional[str]
    thumbnail_url: Optional[str]
    duration_seconds: Optional[int]

    # Patterns
    hook_type: Optional[str]
    emotion: Optional[str]
    pacing: Optional[str]
    content_style: Optional[str]

    # Visual elements
    has_text_overlay: bool
    has_face: bool
    has_music: bool
    has_voiceover: bool

    # Predictions
    viral_probability: float
    predicted_engagement: float
    confidence_score: float

    # Status
    analysis_status: str
    is_benchmark: bool

    # Timestamps
    created_at: datetime
    analyzed_at: Optional[datetime]

    class Config:
        from_attributes = True


class VideoDetailResponse(VideoResponse):
    """Detailed video response with analysis results."""
    analysis_result: Dict[str, Any] = {}
    ai_reasoning: Optional[str]
    timeline: List[Dict[str, Any]] = []
    recommendations: List[Dict[str, Any]] = []

    # Benchmark data (if applicable)
    benchmark_source: Optional[str]
    actual_views: int = 0
    actual_likes: int = 0
    actual_shares: int = 0
    actual_comments: int = 0


# ============================================================================
# Pattern Schemas
# ============================================================================

class PatternBase(BaseModel):
    """Base pattern schema."""
    hook_type: str
    emotion: str
    pacing: str
    content_style: Optional[str] = None


class PatternPerformanceResponse(PatternBase):
    """Schema for pattern performance response."""
    id: UUID
    bayesian_alpha: float
    bayesian_beta: float
    sample_size: int
    avg_viral_score: float
    avg_engagement: float
    confidence_interval_lower: Optional[float]
    confidence_interval_upper: Optional[float]
    source: str
    weight: float

    class Config:
        from_attributes = True


class TopPatternResponse(BaseModel):
    """Schema for top pattern recommendation."""
    hook_type: str
    emotion: str
    pacing: str
    content_style: Optional[str]
    thompson_score: float
    expected_viral_score: float
    uncertainty: float
    sample_size: int
    reasoning: str


# ============================================================================
# Benchmark Schemas
# ============================================================================

class BenchmarkCreate(BaseModel):
    """Schema for creating a benchmark video."""
    name: str
    video_url: str
    benchmark_source: str = "manual"
    actual_views: int = 0
    actual_likes: int = 0
    actual_shares: int = 0
    actual_comments: int = 0


class BenchmarkResponse(VideoResponse):
    """Schema for benchmark video response."""
    benchmark_source: Optional[str]
    actual_views: int
    actual_likes: int
    actual_shares: int
    actual_comments: int


# ============================================================================
# Recommendation Schemas
# ============================================================================

class VideoRecommendations(BaseModel):
    """Recommendations for a specific video."""
    video_id: UUID
    current_patterns: PatternBase
    recommendations: List[RecommendationEntry]
    suggested_patterns: List[TopPatternResponse]
    expected_improvement: float


class PatternRecommendations(BaseModel):
    """Best patterns to use for new videos."""
    top_patterns: List[TopPatternResponse]
    methodology: str = "Thompson Sampling"


# ============================================================================
# Upload Response Schemas
# ============================================================================

class UploadUrlResponse(BaseModel):
    """Response for presigned upload URL."""
    upload_url: str
    file_key: str
    internal_key: str
    expires_in: int


class UploadCompleteRequest(BaseModel):
    """Request to mark upload as complete."""
    internal_key: str
    name: str


# ============================================================================
# Pagination
# ============================================================================

class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    items: List[Any]
    total: int
    skip: int
    limit: int
    has_more: bool

    class Config:
        from_attributes = True


class PaginatedVideoResponse(BaseModel):
    """Paginated response for videos."""
    items: List[VideoResponse]
    total: int
    skip: int
    limit: int
    has_more: bool

    class Config:
        from_attributes = True
