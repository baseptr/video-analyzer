"""
SQLAlchemy models for Video Analyzer.

Models:
- User: Authentication and user management
- Video: Video metadata, patterns, and analysis results
- PatternPerformance: Aggregated pattern statistics for predictions
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, BigInteger, Boolean, DateTime,
    Float, Text, ForeignKey, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database.base import Base


class User(Base):
    """
    User model for authentication.
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Status
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(email={self.email})>"


class Video(Base):
    """
    Video model - main entity for video analysis.

    Stores:
    - Video metadata (URL, duration, etc.)
    - Extracted patterns (hook_type, emotion, pacing, etc.)
    - Analysis results (viral probability, recommendations)
    - Benchmark data (for reference videos)
    """
    __tablename__ = "videos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Video info
    name = Column(String(200), nullable=False)
    video_url = Column(String(500))  # R2 storage URL
    thumbnail_url = Column(String(500))
    duration_seconds = Column(Integer)

    # Extracted patterns (populated by Claude Vision)
    hook_type = Column(String(50), index=True)  # transformation, problem_solution, question, social_proof, etc.
    emotion = Column(String(50), index=True)  # excitement, curiosity, trust, fomo, etc.
    pacing = Column(String(50), index=True)  # fast, medium, slow
    content_style = Column(String(50))  # ugc, talking_head, screen_recording, animation

    # Visual elements
    has_text_overlay = Column(Boolean, default=False)
    has_face = Column(Boolean, default=False)
    has_music = Column(Boolean, default=False)
    has_voiceover = Column(Boolean, default=False)

    # Predictions (from Markov Chain + Thompson Sampling)
    viral_probability = Column(Float, default=0.0)  # 0-1 probability of going viral
    predicted_engagement = Column(Float, default=0.0)  # Predicted engagement rate
    confidence_score = Column(Float, default=0.0)  # Prediction confidence

    # Benchmark data (for reference videos)
    is_benchmark = Column(Boolean, default=False, index=True)
    benchmark_source = Column(String(100))  # tiktok, youtube, instagram, etc.
    actual_views = Column(BigInteger, default=0)
    actual_likes = Column(BigInteger, default=0)
    actual_shares = Column(BigInteger, default=0)
    actual_comments = Column(BigInteger, default=0)

    # Analysis status
    analysis_status = Column(String(20), default='pending')  # pending, processing, completed, failed
    analysis_result = Column(JSON, default={})  # Full Claude Vision analysis result
    ai_reasoning = Column(Text, nullable=True)  # Claude's reasoning explanation

    # Timeline breakdown (from Claude Vision)
    timeline = Column(JSON, default=[])
    """
    Timeline format:
    [
        {
            "timestamp": "0-3s",
            "what_happens": "Hook with question",
            "emotion_shift": "curiosity",
            "retention_hook": "open loop",
            "cta_presence": false
        },
        ...
    ]
    """

    # Recommendations (generated after analysis)
    recommendations = Column(JSON, default=[])
    """
    Recommendations format:
    [
        {
            "type": "hook",
            "suggestion": "Try transformation hook for better retention",
            "expected_improvement": 0.15
        },
        ...
    ]
    """

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    analyzed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="videos")

    def __repr__(self):
        return f"<Video(name={self.name}, viral_prob={self.viral_probability:.2%})>"


class PatternPerformance(Base):
    """
    Aggregated performance by pattern combinations.

    Used by:
    - Markov Chain for viral probability prediction
    - Thompson Sampling for pattern recommendations
    """
    __tablename__ = "pattern_performance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Pattern combination
    hook_type = Column(String(50), index=True)
    emotion = Column(String(50), index=True)
    pacing = Column(String(50), index=True)
    content_style = Column(String(50), index=True)

    # Bayesian parameters (for Thompson Sampling)
    bayesian_alpha = Column(Float, default=1.0)  # Prior alpha (successes)
    bayesian_beta = Column(Float, default=1.0)  # Prior beta (failures)

    # Aggregated metrics from benchmark videos
    sample_size = Column(Integer, default=0)  # Number of videos with this pattern combo
    avg_viral_score = Column(Float, default=0.0)  # Average viral probability
    avg_engagement = Column(Float, default=0.0)  # Average engagement rate

    # Confidence intervals
    confidence_interval_lower = Column(Float, nullable=True)
    confidence_interval_upper = Column(Float, nullable=True)

    # Source tracking
    source = Column(String(50), default='benchmark')  # 'benchmark' or 'user'
    weight = Column(Float, default=1.0)  # benchmark=2.0, user=1.0

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<PatternPerformance(hook={self.hook_type}, emotion={self.emotion}, viral={self.avg_viral_score:.2%})>"
