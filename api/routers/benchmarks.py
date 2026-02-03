"""
Benchmarks router - access to benchmark videos and pattern statistics.
"""

from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.base import get_db
from database.models import User, Video, PatternPerformance
from database.schemas import (
    VideoResponse, BenchmarkResponse, PatternPerformanceResponse,
    PaginatedResponse, TopPatternResponse
)
from api.dependencies import get_current_user
from utils.logger import setup_logger
from utils.markov_chain import MarkovChainPredictor

logger = setup_logger(__name__)

router = APIRouter()


@router.get("/patterns", response_model=List[TopPatternResponse])
async def get_top_patterns(
    metric: str = Query("viral", description="Metric to sort by: viral, engagement"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get top performing pattern combinations from benchmarks.

    Args:
        metric: Metric to sort by (viral, engagement)
        limit: Maximum patterns to return
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of top patterns with performance data
    """
    predictor = MarkovChainPredictor(db)
    top_patterns = predictor.get_best_patterns(metric=metric, top_n=limit)

    # Format response
    results = []
    for pattern in top_patterns:
        results.append(TopPatternResponse(
            hook_type=pattern['hook_type'],
            emotion=pattern['emotion'],
            pacing=pattern['pacing'],
            content_style=pattern.get('content_style'),
            thompson_score=0.0,  # Not used here
            expected_viral_score=pattern['avg_viral_score'],
            uncertainty=0.3,  # Placeholder
            sample_size=pattern['sample_size'],
            reasoning=f"Based on {pattern['sample_size']} benchmark videos with {pattern['avg_viral_score']:.1%} avg viral score"
        ))

    return results


@router.get("/patterns/all", response_model=List[PatternPerformanceResponse])
async def get_all_patterns(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all pattern performance data.

    Args:
        db: Database session
        current_user: Current authenticated user

    Returns:
        List of all pattern performance records
    """
    patterns = db.query(PatternPerformance).order_by(
        PatternPerformance.avg_viral_score.desc()
    ).all()

    return patterns


@router.get("/videos", response_model=PaginatedResponse)
async def list_benchmark_videos(
    skip: int = 0,
    limit: int = 20,
    hook_type: Optional[str] = None,
    emotion: Optional[str] = None,
    pacing: Optional[str] = None,
    min_viral_score: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List benchmark videos.

    Args:
        skip: Number of items to skip
        limit: Maximum items to return
        hook_type: Filter by hook type
        emotion: Filter by emotion
        pacing: Filter by pacing
        min_viral_score: Minimum viral probability
        db: Database session
        current_user: Current authenticated user

    Returns:
        Paginated list of benchmark videos
    """
    query = db.query(Video).filter(
        Video.is_benchmark == True,
        Video.analysis_status == 'completed'
    )

    # Apply filters
    if hook_type:
        query = query.filter(Video.hook_type == hook_type)
    if emotion:
        query = query.filter(Video.emotion == emotion)
    if pacing:
        query = query.filter(Video.pacing == pacing)
    if min_viral_score:
        query = query.filter(Video.viral_probability >= min_viral_score)

    total = query.count()
    videos = query.order_by(Video.viral_probability.desc()).offset(skip).limit(limit).all()

    return {
        "items": videos,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + limit < total
    }


@router.get("/videos/{video_id}", response_model=BenchmarkResponse)
async def get_benchmark_video(
    video_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get benchmark video details.

    Args:
        video_id: Video ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Benchmark video details
    """
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.is_benchmark == True
    ).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Benchmark video not found"
        )

    return video


@router.get("/stats")
async def get_benchmark_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get benchmark statistics summary.

    Args:
        db: Database session
        current_user: Current authenticated user

    Returns:
        Statistics about benchmark data
    """
    # Count benchmark videos
    total_benchmarks = db.query(Video).filter(
        Video.is_benchmark == True,
        Video.analysis_status == 'completed'
    ).count()

    # Count patterns
    total_patterns = db.query(PatternPerformance).count()

    # Get hook type distribution
    hook_types = db.query(
        Video.hook_type,
        func.count(Video.id).label('count')
    ).filter(
        Video.is_benchmark == True,
        Video.analysis_status == 'completed'
    ).group_by(Video.hook_type).all()

    # Get emotion distribution
    emotions = db.query(
        Video.emotion,
        func.count(Video.id).label('count')
    ).filter(
        Video.is_benchmark == True,
        Video.analysis_status == 'completed'
    ).group_by(Video.emotion).all()

    # Get average viral score
    avg_viral = db.query(
        func.avg(Video.viral_probability)
    ).filter(
        Video.is_benchmark == True,
        Video.analysis_status == 'completed'
    ).scalar() or 0

    return {
        "total_benchmarks": total_benchmarks,
        "total_patterns": total_patterns,
        "avg_viral_score": round(float(avg_viral), 4),
        "hook_type_distribution": {h[0]: h[1] for h in hook_types if h[0]},
        "emotion_distribution": {e[0]: e[1] for e in emotions if e[0]},
    }


@router.post("/refresh-patterns")
async def refresh_pattern_performance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Recalculate pattern performance from benchmark videos.

    Admin only - updates PatternPerformance table.

    Args:
        db: Database session
        current_user: Current authenticated user (must be admin)

    Returns:
        Number of patterns updated
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    predictor = MarkovChainPredictor(db)
    result = predictor.update_pattern_performance()

    logger.info(f"Pattern performance refreshed: {result}")

    return result
