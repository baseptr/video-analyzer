"""
Seed benchmark videos and pattern performance data.

Run with: python scripts/seed_benchmarks.py
Or via Makefile: make seed
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from database.base import SessionLocal, init_db
from database.models import Video, PatternPerformance, User
from utils.logger import setup_logger

logger = setup_logger(__name__)


# Sample benchmark data based on viral video patterns
BENCHMARK_PATTERNS = [
    # High-performing patterns
    {
        "hook_type": "transformation",
        "emotion": "curiosity",
        "pacing": "fast",
        "content_style": "ugc",
        "viral_probability": 0.75,
        "predicted_engagement": 0.12,
    },
    {
        "hook_type": "question",
        "emotion": "curiosity",
        "pacing": "medium",
        "content_style": "talking_head",
        "viral_probability": 0.68,
        "predicted_engagement": 0.10,
    },
    {
        "hook_type": "social_proof",
        "emotion": "trust",
        "pacing": "medium",
        "content_style": "ugc",
        "viral_probability": 0.65,
        "predicted_engagement": 0.09,
    },
    {
        "hook_type": "shock",
        "emotion": "excitement",
        "pacing": "fast",
        "content_style": "b_roll",
        "viral_probability": 0.72,
        "predicted_engagement": 0.11,
    },
    {
        "hook_type": "problem_solution",
        "emotion": "hope",
        "pacing": "medium",
        "content_style": "screen_recording",
        "viral_probability": 0.58,
        "predicted_engagement": 0.08,
    },
    # Medium-performing patterns
    {
        "hook_type": "insider_secret",
        "emotion": "fomo",
        "pacing": "fast",
        "content_style": "talking_head",
        "viral_probability": 0.55,
        "predicted_engagement": 0.07,
    },
    {
        "hook_type": "urgency",
        "emotion": "fomo",
        "pacing": "fast",
        "content_style": "animation",
        "viral_probability": 0.50,
        "predicted_engagement": 0.06,
    },
    {
        "hook_type": "transformation",
        "emotion": "achievement",
        "pacing": "slow",
        "content_style": "ugc",
        "viral_probability": 0.45,
        "predicted_engagement": 0.05,
    },
    # Lower-performing patterns (for comparison)
    {
        "hook_type": "question",
        "emotion": "neutral",
        "pacing": "slow",
        "content_style": "screen_recording",
        "viral_probability": 0.25,
        "predicted_engagement": 0.03,
    },
    {
        "hook_type": "problem_solution",
        "emotion": "frustration",
        "pacing": "slow",
        "content_style": "talking_head",
        "viral_probability": 0.30,
        "predicted_engagement": 0.04,
    },
]


def create_anonymous_user(db):
    """Create anonymous user for benchmark videos."""
    anonymous_email = "anonymous@video-analyzer.local"

    user = db.query(User).filter(User.email == anonymous_email).first()
    if not user:
        user = User(
            email=anonymous_email,
            password_hash="$2b$12$anonymous_user_no_login_allowed",
            is_active=True,
            is_admin=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"Created anonymous user: {user.id}")

    return user


def seed_benchmark_videos(db, user):
    """Seed benchmark videos with predefined patterns."""
    existing_count = db.query(Video).filter(Video.is_benchmark == True).count()

    if existing_count > 0:
        logger.info(f"Skipping video seeding: {existing_count} benchmarks already exist")
        return

    for i, pattern in enumerate(BENCHMARK_PATTERNS):
        video = Video(
            user_id=user.id,
            name=f"Benchmark Video {i+1}: {pattern['hook_type']} + {pattern['emotion']}",
            video_url=f"benchmark://sample_{i+1}.mp4",  # Placeholder URL
            hook_type=pattern["hook_type"],
            emotion=pattern["emotion"],
            pacing=pattern["pacing"],
            content_style=pattern["content_style"],
            viral_probability=pattern["viral_probability"],
            predicted_engagement=pattern["predicted_engagement"],
            confidence_score=0.85,
            is_benchmark=True,
            benchmark_source="seed_data",
            analysis_status="completed",
            actual_views=int(pattern["viral_probability"] * 1000000),
            actual_likes=int(pattern["viral_probability"] * 50000),
        )
        db.add(video)

    db.commit()
    logger.info(f"Seeded {len(BENCHMARK_PATTERNS)} benchmark videos")


def seed_pattern_performance(db):
    """Aggregate benchmark videos into pattern performance."""
    existing_count = db.query(PatternPerformance).count()

    if existing_count > 0:
        logger.info(f"Skipping pattern seeding: {existing_count} patterns already exist")
        return

    # Get all benchmark videos
    videos = db.query(Video).filter(
        Video.is_benchmark == True,
        Video.analysis_status == "completed"
    ).all()

    if not videos:
        logger.warning("No benchmark videos found")
        return

    # Group by pattern combinations
    pattern_groups = {}
    for video in videos:
        key = (video.hook_type, video.emotion, video.pacing, video.content_style)
        if key not in pattern_groups:
            pattern_groups[key] = []
        pattern_groups[key].append(video)

    # Create PatternPerformance records
    for (hook_type, emotion, pacing, content_style), group_videos in pattern_groups.items():
        viral_scores = [v.viral_probability for v in group_videos]
        engagement_scores = [v.predicted_engagement for v in group_videos]

        avg_viral = sum(viral_scores) / len(viral_scores)
        avg_engagement = sum(engagement_scores) / len(engagement_scores)

        # Calculate Bayesian parameters
        successes = sum(1 for v in group_videos if v.viral_probability > 0.5)
        failures = len(group_videos) - successes

        pattern = PatternPerformance(
            hook_type=hook_type,
            emotion=emotion,
            pacing=pacing,
            content_style=content_style,
            sample_size=len(group_videos),
            avg_viral_score=avg_viral,
            avg_engagement=avg_engagement,
            bayesian_alpha=1 + successes,
            bayesian_beta=1 + failures,
            confidence_interval_lower=max(0, avg_viral - 0.15),
            confidence_interval_upper=min(1, avg_viral + 0.15),
            source="benchmark",
            weight=2.0,  # Benchmarks have higher weight
        )
        db.add(pattern)

    db.commit()
    logger.info(f"Seeded {len(pattern_groups)} pattern performance records")


def seed_benchmarks():
    """Main seeding function."""
    logger.info("Starting benchmark seeding...")

    init_db()
    db = SessionLocal()

    try:
        # Create anonymous user
        user = create_anonymous_user(db)

        # Seed benchmark videos
        seed_benchmark_videos(db, user)

        # Seed pattern performance
        seed_pattern_performance(db)

        logger.info("Benchmark seeding completed successfully")

    except Exception as e:
        logger.error(f"Seeding failed: {e}")
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_benchmarks()
