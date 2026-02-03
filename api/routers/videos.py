"""
Videos router - upload, list, analyze, delete videos.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session

from database.base import get_db
from database.models import User, Video
from database.schemas import (
    VideoResponse, VideoDetailResponse, VideoCreate,
    UploadUrlResponse, UploadCompleteRequest, PaginatedVideoResponse
)
from api.dependencies import get_current_user
from utils.logger import setup_logger
from utils.storage import get_storage
from utils.video_analyzer import analyze_video_with_retry
from utils.markov_chain import MarkovChainPredictor

logger = setup_logger(__name__)

router = APIRouter()


@router.post("/upload", response_model=VideoDetailResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(...),
    name: str = Form(...),
    auto_analyze: bool = Form(True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload a video for analysis.

    Args:
        video: Video file (MP4, MOV)
        name: Video name
        auto_analyze: Whether to automatically analyze the video
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created video with analysis results (if auto_analyze=True)
    """
    # Validate file type
    if not video.content_type or not video.content_type.startswith('video/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Please upload a video file."
        )

    # Read file content
    file_content = await video.read()

    # Check file size (max 100MB)
    if len(file_content) > 100 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 100MB."
        )

    # Upload to storage
    storage = get_storage()
    video_url = storage.upload_user_video(file_content, video.filename, str(current_user.id))

    # Create video record
    db_video = Video(
        user_id=current_user.id,
        name=name,
        video_url=video_url,
        analysis_status='pending' if auto_analyze else 'skipped',
    )
    db.add(db_video)
    db.commit()
    db.refresh(db_video)

    logger.info(f"Video uploaded: {db_video.id} by user {current_user.email}")

    # Analyze in background if requested
    if auto_analyze:
        background_tasks.add_task(analyze_video_task, str(db_video.id), video_url)

    return db_video


@router.get("/upload-url", response_model=UploadUrlResponse)
async def get_upload_url(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get presigned URL for direct video upload to R2.

    Frontend can use this URL to upload videos directly,
    bypassing the backend server.

    Args:
        filename: Original filename
        current_user: Current authenticated user

    Returns:
        Presigned upload URL and file key
    """
    storage = get_storage()

    try:
        result = storage.get_upload_url(str(current_user.id), filename)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/upload-complete", response_model=VideoDetailResponse)
async def complete_upload(
    data: UploadCompleteRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mark direct upload as complete and trigger analysis.

    Called after frontend uploads video directly to R2.

    Args:
        data: Upload completion data (internal_key, name)
        db: Database session
        current_user: Current authenticated user

    Returns:
        Created video record
    """
    # Create video record
    db_video = Video(
        user_id=current_user.id,
        name=data.name,
        video_url=data.internal_key,
        analysis_status='pending',
    )
    db.add(db_video)
    db.commit()
    db.refresh(db_video)

    logger.info(f"Direct upload completed: {db_video.id} by user {current_user.email}")

    # Trigger analysis
    background_tasks.add_task(analyze_video_task, str(db_video.id), data.internal_key)

    return db_video


@router.get("", response_model=PaginatedVideoResponse)
async def list_videos(
    skip: int = 0,
    limit: int = 20,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List videos for the current user.

    Args:
        skip: Number of items to skip
        limit: Maximum items to return
        status_filter: Filter by analysis status
        db: Database session
        current_user: Current authenticated user

    Returns:
        Paginated list of videos
    """
    query = db.query(Video).filter(Video.user_id == current_user.id)

    if status_filter:
        query = query.filter(Video.analysis_status == status_filter)

    total = query.count()
    videos = query.order_by(Video.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "items": videos,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": skip + limit < total
    }


@router.get("/{video_id}", response_model=VideoDetailResponse)
async def get_video(
    video_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get video details.

    Args:
        video_id: Video ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Video details with analysis results
    """
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == current_user.id
    ).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    return video


@router.get("/{video_id}/analysis", response_model=VideoDetailResponse)
async def get_video_analysis(
    video_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get video analysis results.

    Args:
        video_id: Video ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Video with analysis results
    """
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == current_user.id
    ).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    if video.analysis_status == 'pending':
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="Analysis in progress"
        )

    if video.analysis_status == 'failed':
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis failed"
        )

    return video


@router.post("/{video_id}/analyze", response_model=VideoDetailResponse)
async def trigger_analysis(
    video_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Trigger analysis for a video.

    Args:
        video_id: Video ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Video with updated status
    """
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == current_user.id
    ).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    if video.analysis_status == 'processing':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analysis already in progress"
        )

    # Update status and trigger analysis
    video.analysis_status = 'pending'
    db.commit()

    background_tasks.add_task(analyze_video_task, str(video.id), video.video_url)

    return video


@router.delete("/{video_id}")
async def delete_video(
    video_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a video.

    Args:
        video_id: Video ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Success message
    """
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == current_user.id
    ).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    # Delete from storage
    if video.video_url:
        storage = get_storage()
        storage.delete_video(video.video_url)

    # Delete from database
    db.delete(video)
    db.commit()

    logger.info(f"Video deleted: {video_id} by user {current_user.email}")

    return {"message": "Video deleted successfully"}


@router.get("/{video_id}/access-url")
async def get_video_access_url(
    video_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get temporary access URL for video playback.

    Args:
        video_id: Video ID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Presigned URL for video access
    """
    video = db.query(Video).filter(
        Video.id == video_id,
        Video.user_id == current_user.id
    ).first()

    if not video:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )

    storage = get_storage()
    access_url = storage.generate_access_url(video.video_url)

    return {"access_url": access_url, "expires_in": 3600}


# ============================================================================
# Background Tasks
# ============================================================================

def analyze_video_task(video_id: str, video_url: str):
    """
    Background task to analyze a video.
    """
    from database.base import SessionLocal

    db = SessionLocal()
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            logger.error(f"Video not found for analysis: {video_id}")
            return

        # Update status
        video.analysis_status = 'processing'
        db.commit()

        logger.info(f"Starting analysis for video: {video_id}")

        # Analyze video
        result = analyze_video_with_retry(video_url)

        if result:
            # Update video with results
            video.hook_type = result.get('hook_type')
            video.emotion = result.get('emotion')
            video.pacing = result.get('pacing')
            video.content_style = result.get('content_style')
            video.has_text_overlay = result.get('has_text_overlay', False)
            video.has_face = result.get('has_face', False)
            video.has_music = result.get('has_music', False)
            video.has_voiceover = result.get('has_voiceover', False)
            video.viral_probability = result.get('viral_probability', 0)
            video.predicted_engagement = result.get('predicted_engagement', 0)
            video.timeline = result.get('timeline', [])
            video.recommendations = result.get('recommendations', [])
            video.ai_reasoning = result.get('reasoning')
            video.analysis_result = result
            video.analysis_status = 'completed'
            video.analyzed_at = datetime.utcnow()

            # Calculate confidence score using Markov Chain
            predictor = MarkovChainPredictor(db)
            prediction = predictor.predict_viral_probability(
                hook_type=video.hook_type or 'unknown',
                emotion=video.emotion or 'unknown',
                pacing=video.pacing or 'unknown',
                content_style=video.content_style
            )
            video.confidence_score = prediction.get('confidence_score', 0)

            logger.info(f"Analysis completed for video: {video_id}, viral_prob: {video.viral_probability:.2%}")
        else:
            video.analysis_status = 'failed'
            video.ai_reasoning = "Analysis failed - could not process video"
            logger.error(f"Analysis failed for video: {video_id}")

        db.commit()

    except Exception as e:
        logger.error(f"Error analyzing video {video_id}: {e}")
        try:
            video = db.query(Video).filter(Video.id == video_id).first()
            if video:
                video.analysis_status = 'failed'
                video.ai_reasoning = f"Analysis error: {str(e)}"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
