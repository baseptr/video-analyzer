"""
Thompson Sampling for pattern optimization.

Balances between:
- Exploitation: Using proven patterns (high viral score)
- Exploration: Testing new patterns (might surprise)

Used to recommend which patterns to use for new videos.
"""

import logging
from typing import List, Dict, Optional
import numpy as np
from sqlalchemy.orm import Session

from database.models import PatternPerformance, Video

logger = logging.getLogger(__name__)


class ThompsonSamplingOptimizer:
    """
    Thompson Sampling for Multi-Armed Bandit pattern selection.

    Selects top-N patterns for recommendations,
    balancing between exploit (known winners) and explore (new patterns).
    """

    def __init__(self, db: Session):
        self.db = db

    def select_next_patterns(self, n_patterns: int = 5) -> List[Dict]:
        """
        Select top-N patterns for recommendations.

        Args:
            n_patterns: Number of patterns to recommend

        Returns:
            List[Dict]: Patterns sorted by priority
        """
        # Get all tested patterns
        patterns = self.db.query(PatternPerformance).all()

        if not patterns:
            return self._get_default_patterns(n_patterns)

        pattern_scores = []

        for pattern in patterns:
            score = self._calculate_thompson_score(pattern)
            pattern_scores.append(score)

        # Sort by priority (Thompson Sampling score)
        pattern_scores.sort(key=lambda x: x['priority'], reverse=True)

        # Add recommendations
        for i, pattern in enumerate(pattern_scores[:n_patterns]):
            pattern['rank'] = i + 1
            pattern['reasoning'] = self._generate_reasoning(pattern)

        return pattern_scores[:n_patterns]

    def _calculate_thompson_score(self, pattern: PatternPerformance) -> Dict:
        """
        Calculate Thompson Sampling score for a pattern.

        Uses Beta distribution: Beta(alpha, beta)
        - alpha = bayesian_alpha (successes)
        - beta = bayesian_beta (failures)

        Thompson Sampling formula:
        score = numpy.random.beta(alpha, beta)
        """
        alpha = pattern.bayesian_alpha or 1.0
        beta = pattern.bayesian_beta or 1.0

        # Thompson Sampling: random sample from Beta distribution
        sampled_score = np.random.beta(alpha, beta)

        # Uncertainty (high = need more data)
        uncertainty = beta / (alpha + beta)

        # Expected score (mean) = alpha / (alpha + beta)
        expected_score = alpha / (alpha + beta)

        # Weight multiplier (benchmark patterns have weight=2.0)
        weight = pattern.weight or 1.0

        return {
            'hook_type': pattern.hook_type,
            'emotion': pattern.emotion,
            'pacing': pattern.pacing,
            'content_style': pattern.content_style,
            'expected_viral_score': round(expected_score, 4),
            'sampled_score': round(float(sampled_score), 4),
            'uncertainty': round(float(uncertainty), 3),
            'priority': float(sampled_score) * weight,
            'sample_size': pattern.sample_size,
            'alpha': alpha,
            'beta': beta,
            'weight': weight,
            'source': pattern.source or 'benchmark'
        }

    def _generate_reasoning(self, pattern: Dict) -> str:
        """Generate human-readable explanation for pattern selection."""
        score = pattern['expected_viral_score']
        uncertainty = pattern['uncertainty']
        sample_size = pattern['sample_size']

        if score > 0.6 and uncertainty < 0.3:
            return f"High viral potential ({score:.1%}) + low uncertainty (tested {sample_size} times) - proven winner!"

        elif score > 0.6 and uncertainty >= 0.3:
            return f"High viral potential ({score:.1%}) but high uncertainty - needs more tests to confirm"

        elif score < 0.3 and uncertainty > 0.5:
            return f"Low viral score ({score:.1%}) + high uncertainty - risky, but might surprise (explore)"

        elif uncertainty > 0.6:
            return f"High uncertainty (only {sample_size} tests) - exploration opportunity"

        else:
            return f"Moderate viral potential ({score:.1%}) - balanced choice"

    def _get_default_patterns(self, n_patterns: int) -> List[Dict]:
        """Return default patterns if no data available."""
        default = [
            {
                'hook_type': 'transformation',
                'emotion': 'curiosity',
                'pacing': 'fast',
                'content_style': 'ugc',
                'expected_viral_score': 0.0,
                'priority': 1.0,
                'reasoning': 'Transformation hooks are highly effective for viral content'
            },
            {
                'hook_type': 'question',
                'emotion': 'curiosity',
                'pacing': 'medium',
                'content_style': 'talking_head',
                'expected_viral_score': 0.0,
                'priority': 0.9,
                'reasoning': 'Question hooks create curiosity gaps that drive engagement'
            },
            {
                'hook_type': 'social_proof',
                'emotion': 'trust',
                'pacing': 'medium',
                'content_style': 'ugc',
                'expected_viral_score': 0.0,
                'priority': 0.8,
                'reasoning': 'Social proof builds trust and credibility'
            },
            {
                'hook_type': 'problem_solution',
                'emotion': 'hope',
                'pacing': 'medium',
                'content_style': 'screen_recording',
                'expected_viral_score': 0.0,
                'priority': 0.7,
                'reasoning': 'Problem-solution format is clear and actionable'
            },
            {
                'hook_type': 'shock',
                'emotion': 'excitement',
                'pacing': 'fast',
                'content_style': 'b_roll',
                'expected_viral_score': 0.0,
                'priority': 0.6,
                'reasoning': 'Shock value grabs attention quickly'
            }
        ]

        for i, pattern in enumerate(default[:n_patterns]):
            pattern['rank'] = i + 1
            pattern['sample_size'] = 0
            pattern['uncertainty'] = 1.0

        return default[:n_patterns]


def thompson_sampling(db: Session, n_recommendations: int = 5) -> List[Dict]:
    """
    Thompson Sampling for getting top patterns.

    Wrapper function for use in recommendations endpoint.

    Args:
        db: Database session
        n_recommendations: Number of recommendations

    Returns:
        List[Dict] with top patterns
    """
    patterns = db.query(PatternPerformance).all()

    if not patterns:
        logger.warning("No patterns found in database")
        return []

    results = []
    for pattern in patterns:
        alpha = pattern.bayesian_alpha or 1.0
        beta = pattern.bayesian_beta or 1.0
        weight = pattern.weight or 1.0

        # Thompson score
        thompson_score = np.random.beta(alpha, beta) * weight

        results.append({
            'pattern_id': str(pattern.id),
            'hook_type': pattern.hook_type,
            'emotion': pattern.emotion,
            'pacing': pattern.pacing,
            'content_style': pattern.content_style,
            'thompson_score': thompson_score,
            'alpha': alpha,
            'beta': beta,
            'weight': weight,
            'sample_size': pattern.sample_size or 0,
            'mean_viral_score': alpha / (alpha + beta) if (alpha + beta) > 0 else 0,
        })

    # Sort by Thompson score
    results.sort(key=lambda x: x['thompson_score'], reverse=True)

    return results[:n_recommendations]


def get_pattern_recommendations_for_video(
    db: Session,
    video: Video,
    n_recommendations: int = 3
) -> List[Dict]:
    """
    Get specific pattern recommendations to improve a video.

    Args:
        db: Database session
        video: Video to get recommendations for
        n_recommendations: Number of recommendations

    Returns:
        List of recommendations with expected improvement
    """
    # Get best patterns
    best_patterns = thompson_sampling(db, n_recommendations * 2)

    if not best_patterns:
        return []

    recommendations = []

    for pattern in best_patterns:
        # Check if pattern is different from current video
        if pattern['hook_type'] == video.hook_type and pattern['emotion'] == video.emotion:
            continue

        improvement = pattern['mean_viral_score'] - (video.viral_probability or 0)

        if improvement > 0:
            rec = {
                'type': 'pattern',
                'current': {
                    'hook_type': video.hook_type,
                    'emotion': video.emotion,
                    'pacing': video.pacing
                },
                'suggested': {
                    'hook_type': pattern['hook_type'],
                    'emotion': pattern['emotion'],
                    'pacing': pattern['pacing'],
                    'content_style': pattern['content_style']
                },
                'expected_improvement': round(improvement, 4),
                'confidence': round(pattern['mean_viral_score'], 4),
                'reasoning': f"Switching to {pattern['hook_type']} hook with {pattern['emotion']} emotion could improve viral potential by {improvement:.1%}"
            }
            recommendations.append(rec)

            if len(recommendations) >= n_recommendations:
                break

    return recommendations
