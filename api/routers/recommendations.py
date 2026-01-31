"""
Recommendations router - get recommendations for videos and patterns.
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from database.base import get_db
from database.models import User, Video
from database.schemas import (
    VideoRecommendations, PatternRecommendations, TopPatternResponse
)
from api.dependencies import get_current_user
from utils.logger import setup_logger
from utils.thompson_sampling import (
    ThompsonSamplingOptimizer,
    thompson_sampling,
    get_pattern_recommendations_for_video
)

logger = setup_logger(__name__)

router = APIRouter()


@router.get("/videos/{video_id}/recommendations", response_model=VideoRecommendations)
async def get_video_recommendations(
    video_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get recommendations to improve a specific video.

    Uses Thompson Sampling to suggest pattern changes
    that could improve viral potential.

    Args:
        video_id: Video ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Recommendations for improving the video
    """
    # Get video
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == current_user.id
    ).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    if video.analysis_status != 'completed':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video analysis not completed yet"
        )

    # Get pattern recommendations
    recommendations = get_pattern_recommendations_for_video(db, video)

    # Get top patterns for comparison
    optimizer = ThompsonSamplingOptimizer(db)
    suggested_patterns = optimizer.select_next_patterns(n_patterns=3)

    # Calculate expected improvement
    current_viral = video.viral_probability or 0
    best_expected = max([p.get('expected_viral_score', 0) for p in suggested_patterns]) if suggested_patterns else current_viral
    expected_improvement = max(0, best_expected - current_viral)

    return VideoRecommendations(
        video_id=video.id,
        current_patterns={
            "hook_type": video.hook_type or "unknown",
            "emotion": video.emotion or "unknown",
            "pacing": video.pacing or "unknown",
            "content_style": video.content_style
        },
        recommendations=[
            {
                "type": rec['type'],
                "suggestion": rec['reasoning'],
                "expected_improvement": rec['expected_improvement']
            }
            for rec in recommendations
        ] + (video.recommendations or []),
        suggested_patterns=[
            TopPatternResponse(
                hook_type=p['hook_type'],
                emotion=p['emotion'],
                pacing=p['pacing'],
                content_style=p.get('content_style'),
                thompson_score=p.get('priority', 0),
                expected_viral_score=p.get('expected_viral_score', 0),
                uncertainty=p.get('uncertainty', 0.5),
                sample_size=p.get('sample_size', 0),
                reasoning=p.get('reasoning', '')
            )
            for p in suggested_patterns
        ],
        expected_improvement=expected_improvement
    )


@router.get("/patterns", response_model=PatternRecommendations)
async def get_pattern_recommendations(
    n_recommendations: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get recommended patterns for new videos.

    Uses Thompson Sampling to balance exploitation
    (proven patterns) vs exploration (new patterns).

    Args:
        n_recommendations: Number of patterns to recommend
        db: Database session
        current_user: Current authenticated user

    Returns:
        Recommended patterns with scores
    """
    optimizer = ThompsonSamplingOptimizer(db)
    patterns = optimizer.select_next_patterns(n_patterns=n_recommendations)

    return PatternRecommendations(
        top_patterns=[
            TopPatternResponse(
                hook_type=p['hook_type'],
                emotion=p['emotion'],
                pacing=p['pacing'],
                content_style=p.get('content_style'),
                thompson_score=p.get('priority', 0),
                expected_viral_score=p.get('expected_viral_score', 0),
                uncertainty=p.get('uncertainty', 0.5),
                sample_size=p.get('sample_size', 0),
                reasoning=p.get('reasoning', '')
            )
            for p in patterns
        ],
        methodology="Thompson Sampling with Beta distribution priors from benchmark data"
    )


@router.get("/compare")
async def compare_patterns(
    hook_type: str = Query(..., description="Hook type to compare"),
    emotion: str = Query(..., description="Emotion to compare"),
    pacing: str = Query(..., description="Pacing to compare"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Compare a pattern combination against benchmarks.

    Args:
        hook_type: Hook type
        emotion: Emotion
        pacing: Pacing
        db: Database session
        current_user: Current authenticated user

    Returns:
        Comparison results with similar patterns
    """
    from utils.markov_chain import MarkovChainPredictor

    predictor = MarkovChainPredictor(db)

    # Get prediction for the input pattern
    prediction = predictor.predict_viral_probability(
        hook_type=hook_type,
        emotion=emotion,
        pacing=pacing
    )

    # Get top patterns for comparison
    top_patterns = predictor.get_best_patterns(metric="viral", top_n=5)

    # Find rank of input pattern among top patterns
    rank = None
    for i, p in enumerate(top_patterns):
        if (p['hook_type'] == hook_type and
            p['emotion'] == emotion and
            p['pacing'] == pacing):
            rank = i + 1
            break

    return {
        "input_pattern": {
            "hook_type": hook_type,
            "emotion": emotion,
            "pacing": pacing
        },
        "prediction": prediction,
        "rank_among_top_patterns": rank,
        "top_patterns": top_patterns,
        "recommendation": _get_comparison_recommendation(prediction, top_patterns)
    }


def _get_comparison_recommendation(prediction: dict, top_patterns: list) -> str:
    """Generate recommendation based on pattern comparison."""
    viral_prob = prediction.get('viral_probability', 0)

    if viral_prob >= 0.6:
        return "Excellent pattern combination! This has high viral potential."
    elif viral_prob >= 0.4:
        return "Good pattern combination. Consider the top patterns for potential improvement."
    elif viral_prob >= 0.2:
        return "Average pattern combination. Review the top patterns for better alternatives."
    else:
        return "Low viral potential. Strongly recommend using one of the proven top patterns."


@router.get("/trending")
async def get_trending_patterns(
    limit: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get trending patterns based on recent benchmark performance.

    Args:
        limit: Number of patterns to return
        db: Database session
        current_user: Current authenticated user

    Returns:
        Trending patterns
    """
    # Get patterns with highest uncertainty (exploration opportunities)
    patterns = thompson_sampling(db, n_recommendations=limit * 2)

    # Sort by Thompson score which naturally balances exploration/exploitation
    trending = sorted(patterns, key=lambda x: x['thompson_score'], reverse=True)[:limit]

    return {
        "trending_patterns": trending,
        "methodology": "Thompson Sampling identifies patterns with good performance AND high potential for improvement"
    }
