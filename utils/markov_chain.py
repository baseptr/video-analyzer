"""
Markov Chain model for viral probability prediction.

Uses historical pattern performance to predict viral potential
for new videos based on extracted patterns.

Theory:
- P(viral | pattern) = observed viral rate from benchmark data
- For pattern combinations: P(viral | hook, emotion, pacing) = joint probability
- Smoothing: Laplace smoothing to handle unseen patterns
- Bayesian: Use benchmark data as prior when user sample size is small
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy import stats
from sqlalchemy.orm import Session
from database.models import PatternPerformance, Video


class MarkovChainPredictor:
    """
    Predicts video viral potential based on pattern combinations.
    """

    def __init__(self, db: Session):
        self.db = db
        self.alpha = 1.0  # Laplace smoothing
        self.min_sample_size = 5

    def predict_viral_probability(
        self,
        hook_type: str,
        emotion: str,
        pacing: str,
        content_style: Optional[str] = None
    ) -> Dict:
        """
        Predict viral probability for a video with given patterns.

        Returns:
            {
                "viral_probability": 0.65,
                "confidence_score": 0.85,
                "sample_size": 50,
                "confidence_interval": (0.55, 0.75),
                "prediction_method": "exact_match" | "partial_match" | "bayesian_estimate"
            }
        """
        # Try exact pattern match first
        exact_match = self._find_exact_pattern(hook_type, emotion, pacing, content_style)
        if exact_match and exact_match["sample_size"] >= self.min_sample_size:
            return self._format_prediction(exact_match, "exact_match")

        # Try partial matches
        partial_match = self._find_partial_patterns(hook_type, emotion, pacing, content_style)
        if partial_match and partial_match["sample_size"] >= self.min_sample_size / 2:
            return self._format_prediction(partial_match, "partial_match")

        # Fall back to Bayesian estimate
        bayesian_estimate = self._bayesian_estimate(hook_type, emotion, pacing, content_style)
        return self._format_prediction(bayesian_estimate, "bayesian_estimate")

    def _find_exact_pattern(
        self,
        hook_type: str,
        emotion: str,
        pacing: str,
        content_style: Optional[str]
    ) -> Optional[Dict]:
        """Find exact pattern match in performance data."""
        query = self.db.query(PatternPerformance).filter(
            PatternPerformance.hook_type == hook_type,
            PatternPerformance.emotion == emotion,
            PatternPerformance.pacing == pacing
        )

        if content_style:
            query = query.filter(PatternPerformance.content_style == content_style)

        pattern_perf = query.first()

        if not pattern_perf:
            return None

        return {
            "avg_viral_score": pattern_perf.avg_viral_score,
            "sample_size": pattern_perf.sample_size,
            "confidence_interval_lower": pattern_perf.confidence_interval_lower,
            "confidence_interval_upper": pattern_perf.confidence_interval_upper,
        }

    def _find_partial_patterns(
        self,
        hook_type: str,
        emotion: str,
        pacing: str,
        content_style: Optional[str]
    ) -> Optional[Dict]:
        """Find partial pattern matches and combine using weighted average."""
        # Get all benchmark videos with matching individual patterns
        videos = self.db.query(Video).filter(
            Video.is_benchmark == True,
            Video.analysis_status == 'completed'
        ).filter(
            (Video.hook_type == hook_type) |
            (Video.emotion == emotion) |
            (Video.pacing == pacing)
        ).all()

        if not videos:
            return None

        # Weight by number of matching patterns
        weighted_score = 0
        total_weight = 0
        total_sample = 0

        for video in videos:
            matches = 0
            if video.hook_type == hook_type:
                matches += 1
            if video.emotion == emotion:
                matches += 1
            if video.pacing == pacing:
                matches += 1

            weight = matches
            weighted_score += video.viral_probability * weight
            total_weight += weight
            total_sample += 1

        if total_weight == 0:
            return None

        avg_viral = weighted_score / total_weight
        ci_lower, ci_upper = self._calculate_confidence_interval_from_scores(
            [v.viral_probability for v in videos]
        )

        return {
            "avg_viral_score": avg_viral,
            "sample_size": total_sample,
            "confidence_interval_lower": ci_lower,
            "confidence_interval_upper": ci_upper,
        }

    def _bayesian_estimate(
        self,
        hook_type: str,
        emotion: str,
        pacing: str,
        content_style: Optional[str]
    ) -> Dict:
        """Bayesian estimate using benchmark data as prior."""
        # Get all benchmark videos
        all_videos = self.db.query(Video).filter(
            Video.is_benchmark == True,
            Video.analysis_status == 'completed'
        ).all()

        if not all_videos:
            # No data - use conservative baseline
            return {
                "avg_viral_score": 0.3,
                "sample_size": 0,
                "confidence_interval_lower": 0.1,
                "confidence_interval_upper": 0.5,
            }

        # Calculate prior from all benchmarks
        prior_scores = [v.viral_probability for v in all_videos]
        prior_mean = np.mean(prior_scores)
        prior_std = np.std(prior_scores)

        # Get individual pattern data
        hook_data = self._get_single_pattern_data("hook_type", hook_type)
        emotion_data = self._get_single_pattern_data("emotion", emotion)
        pacing_data = self._get_single_pattern_data("pacing", pacing)

        # Bayesian update: combine prior with pattern evidence
        evidence_scores = []
        for data in [hook_data, emotion_data, pacing_data]:
            if data:
                evidence_scores.extend(data)

        if evidence_scores:
            # Weighted combination of prior and evidence
            combined_mean = (prior_mean + np.mean(evidence_scores)) / 2
        else:
            combined_mean = prior_mean

        # Estimate confidence interval
        ci_lower = max(0, combined_mean - 1.96 * prior_std)
        ci_upper = min(1, combined_mean + 1.96 * prior_std)

        return {
            "avg_viral_score": combined_mean,
            "sample_size": len(all_videos),
            "confidence_interval_lower": ci_lower,
            "confidence_interval_upper": ci_upper,
        }

    def _get_single_pattern_data(self, pattern_type: str, pattern_value: str) -> Optional[List[float]]:
        """Get viral scores for videos with a single pattern."""
        videos = self.db.query(Video).filter(
            Video.is_benchmark == True,
            Video.analysis_status == 'completed',
            getattr(Video, pattern_type) == pattern_value
        ).all()

        if not videos:
            return None

        return [v.viral_probability for v in videos]

    def _calculate_confidence_interval_from_scores(
        self,
        scores: List[float],
        confidence_level: float = 0.95
    ) -> Tuple[float, float]:
        """Calculate confidence interval from list of scores."""
        if not scores:
            return (0.0, 0.0)

        mean = np.mean(scores)
        std = np.std(scores)
        n = len(scores)

        if n < 2:
            return (max(0, mean - 0.2), min(1, mean + 0.2))

        z = stats.norm.ppf(1 - (1 - confidence_level) / 2)
        margin = z * std / np.sqrt(n)

        return (max(0, mean - margin), min(1, mean + margin))

    def _format_prediction(self, data: Dict, method: str) -> Dict:
        """Format prediction result with confidence score."""
        viral_prob = data["avg_viral_score"]
        sample_size = data["sample_size"]
        ci_lower = data.get("confidence_interval_lower", viral_prob * 0.7)
        ci_upper = data.get("confidence_interval_upper", min(1, viral_prob * 1.3))

        ci_width = ci_upper - ci_lower
        ci_width_normalized = min(1.0, ci_width / viral_prob) if viral_prob > 0 else 1.0

        # Confidence decreases with wider CI and smaller sample
        sample_confidence = min(1.0, sample_size / 30)
        ci_confidence = 1.0 - ci_width_normalized

        confidence_score = (sample_confidence * 0.6 + ci_confidence * 0.4)

        return {
            "viral_probability": round(viral_prob, 4),
            "viral_probability_percent": round(viral_prob * 100, 2),
            "confidence_score": round(confidence_score, 2),
            "sample_size": sample_size,
            "confidence_interval": (round(ci_lower, 4), round(ci_upper, 4)),
            "confidence_interval_percent": (round(ci_lower * 100, 2), round(ci_upper * 100, 2)),
            "prediction_method": method,
        }

    def update_pattern_performance(self):
        """Recalculate aggregated pattern performance from benchmark videos."""
        videos = self.db.query(Video).filter(
            Video.is_benchmark == True,
            Video.analysis_status == 'completed'
        ).all()

        # Group by pattern combinations
        pattern_groups = {}

        for video in videos:
            key = (
                video.hook_type or "unknown",
                video.emotion or "unknown",
                video.pacing or "unknown",
                video.content_style or "unknown"
            )

            if key not in pattern_groups:
                pattern_groups[key] = []

            pattern_groups[key].append(video)

        # Update or create PatternPerformance records
        for pattern_key, group_videos in pattern_groups.items():
            hook_type, emotion, pacing, content_style = pattern_key

            viral_scores = [v.viral_probability for v in group_videos]
            avg_viral = np.mean(viral_scores) if viral_scores else 0
            avg_engagement = np.mean([v.predicted_engagement for v in group_videos]) if group_videos else 0

            ci_lower, ci_upper = self._calculate_confidence_interval_from_scores(viral_scores)

            # Check if record exists
            existing = self.db.query(PatternPerformance).filter(
                PatternPerformance.hook_type == hook_type,
                PatternPerformance.emotion == emotion,
                PatternPerformance.pacing == pacing,
                PatternPerformance.content_style == content_style
            ).first()

            if existing:
                existing.sample_size = len(group_videos)
                existing.avg_viral_score = avg_viral
                existing.avg_engagement = avg_engagement
                existing.confidence_interval_lower = ci_lower
                existing.confidence_interval_upper = ci_upper
                # Update Bayesian parameters
                existing.bayesian_alpha = 1 + sum(1 for v in group_videos if v.viral_probability > 0.5)
                existing.bayesian_beta = 1 + sum(1 for v in group_videos if v.viral_probability <= 0.5)
            else:
                new_pattern = PatternPerformance(
                    hook_type=hook_type,
                    emotion=emotion,
                    pacing=pacing,
                    content_style=content_style,
                    sample_size=len(group_videos),
                    avg_viral_score=avg_viral,
                    avg_engagement=avg_engagement,
                    confidence_interval_lower=ci_lower,
                    confidence_interval_upper=ci_upper,
                    bayesian_alpha=1 + sum(1 for v in group_videos if v.viral_probability > 0.5),
                    bayesian_beta=1 + sum(1 for v in group_videos if v.viral_probability <= 0.5),
                    source='benchmark',
                    weight=2.0
                )
                self.db.add(new_pattern)

        self.db.commit()

        return {
            "pattern_groups_updated": len(pattern_groups),
            "total_videos_processed": len(videos)
        }

    def get_best_patterns(self, metric: str = "viral", top_n: int = 10) -> List[Dict]:
        """Get top performing pattern combinations."""
        query = self.db.query(PatternPerformance).filter(
            PatternPerformance.sample_size >= self.min_sample_size
        )

        if metric == "viral":
            query = query.order_by(PatternPerformance.avg_viral_score.desc())
        elif metric == "engagement":
            query = query.order_by(PatternPerformance.avg_engagement.desc())

        top_patterns = query.limit(top_n).all()

        results = []
        for pattern in top_patterns:
            results.append({
                "hook_type": pattern.hook_type,
                "emotion": pattern.emotion,
                "pacing": pattern.pacing,
                "content_style": pattern.content_style,
                "avg_viral_score": pattern.avg_viral_score,
                "avg_engagement": pattern.avg_engagement,
                "sample_size": pattern.sample_size,
                "confidence_interval": (
                    pattern.confidence_interval_lower,
                    pattern.confidence_interval_upper
                )
            })

        return results
