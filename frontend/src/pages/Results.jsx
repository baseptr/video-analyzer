import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, CheckCircle, TrendingUp, Lightbulb, Clock,
  Loader2, AlertCircle, Zap, Target, BarChart3
} from 'lucide-react'
import { videoAPI, recommendationAPI } from '../services/api'

const Results = () => {
  const { videoId } = useParams()
  const navigate = useNavigate()
  const [video, setVideo] = useState(null)
  const [recommendations, setRecommendations] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchData()
  }, [videoId])

  const fetchData = async () => {
    try {
      const [videoRes, recsRes] = await Promise.all([
        videoAPI.getVideo(videoId),
        recommendationAPI.getVideoRecommendations(videoId).catch(() => null)
      ])
      setVideo(videoRes.data)
      setRecommendations(recsRes?.data)
    } catch (err) {
      setError('Failed to load video data')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const getViralScoreColor = (score) => {
    if (score >= 0.6) return 'text-green-600'
    if (score >= 0.4) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getViralScoreBg = (score) => {
    if (score >= 0.6) return 'bg-green-100'
    if (score >= 0.4) return 'bg-yellow-100'
    return 'bg-red-100'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }

  if (error || !video) {
    return (
      <div className="card text-center py-12">
        <AlertCircle className="w-16 h-16 mx-auto text-red-400 mb-4" />
        <h2 className="text-xl font-bold text-gray-900 mb-2">Error Loading Video</h2>
        <p className="text-gray-500 mb-4">{error || 'Video not found'}</p>
        <button onClick={() => navigate('/dashboard')} className="btn btn-primary">
          Back to Dashboard
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/dashboard')}
          className="p-2 hover:bg-gray-100 rounded-lg"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{video.name}</h1>
          <p className="text-gray-500">
            Uploaded {new Date(video.created_at).toLocaleString()}
          </p>
        </div>
      </div>

      {/* Main Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Viral Probability */}
        <div className={`card ${getViralScoreBg(video.viral_probability)}`}>
          <div className="flex items-center gap-4">
            <div className="p-3 bg-white rounded-lg">
              <TrendingUp className={`w-8 h-8 ${getViralScoreColor(video.viral_probability)}`} />
            </div>
            <div>
              <p className="text-sm text-gray-600">Viral Probability</p>
              <p className={`text-4xl font-bold ${getViralScoreColor(video.viral_probability)}`}>
                {(video.viral_probability * 100).toFixed(0)}%
              </p>
            </div>
          </div>
        </div>

        {/* Engagement */}
        <div className="card">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-100 rounded-lg">
              <BarChart3 className="w-8 h-8 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Predicted Engagement</p>
              <p className="text-4xl font-bold text-blue-600">
                {(video.predicted_engagement * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        </div>

        {/* Confidence */}
        <div className="card">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-purple-100 rounded-lg">
              <Target className="w-8 h-8 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-gray-600">Confidence Score</p>
              <p className="text-4xl font-bold text-purple-600">
                {(video.confidence_score * 100).toFixed(0)}%
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Patterns */}
      <div className="card">
        <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-yellow-500" />
          Detected Patterns
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500 mb-1">Hook Type</p>
            <p className="font-bold text-gray-900 capitalize">{video.hook_type || '-'}</p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500 mb-1">Emotion</p>
            <p className="font-bold text-gray-900 capitalize">{video.emotion || '-'}</p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500 mb-1">Pacing</p>
            <p className="font-bold text-gray-900 capitalize">{video.pacing || '-'}</p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-500 mb-1">Content Style</p>
            <p className="font-bold text-gray-900 capitalize">{video.content_style || '-'}</p>
          </div>
        </div>

        {/* Visual Elements */}
        <div className="mt-4 flex flex-wrap gap-2">
          {video.has_text_overlay && <span className="badge badge-blue">Text Overlay</span>}
          {video.has_face && <span className="badge badge-blue">Face Visible</span>}
          {video.has_music && <span className="badge badge-blue">Music</span>}
          {video.has_voiceover && <span className="badge badge-blue">Voiceover</span>}
        </div>
      </div>

      {/* Timeline */}
      {video.timeline && video.timeline.length > 0 && (
        <div className="card">
          <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Clock className="w-5 h-5 text-blue-500" />
            Timeline Breakdown
          </h2>
          <div className="space-y-4">
            {video.timeline.map((entry, index) => (
              <div key={index} className="p-4 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <span className="badge badge-blue">{entry.timestamp}</span>
                  {entry.cta_presence && <span className="badge badge-green">CTA</span>}
                </div>
                <p className="font-medium text-gray-900">{entry.what_happens}</p>
                <p className="text-sm text-gray-600 mt-1">
                  <span className="text-gray-500">Emotion shift:</span> {entry.emotion_shift}
                </p>
                <p className="text-sm text-gray-600">
                  <span className="text-gray-500">Retention hook:</span> {entry.retention_hook}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      <div className="card">
        <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
          <Lightbulb className="w-5 h-5 text-yellow-500" />
          Recommendations
        </h2>

        {video.recommendations && video.recommendations.length > 0 ? (
          <div className="space-y-3">
            {video.recommendations.map((rec, index) => (
              <div key={index} className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                <div className="flex items-center justify-between mb-2">
                  <span className="badge badge-yellow capitalize">{rec.type}</span>
                  {rec.expected_improvement > 0 && (
                    <span className="text-sm text-green-600 font-medium">
                      +{(rec.expected_improvement * 100).toFixed(0)}% potential
                    </span>
                  )}
                </div>
                <p className="text-gray-900">{rec.suggestion}</p>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No specific recommendations available.</p>
        )}

        {/* Suggested Patterns from Thompson Sampling */}
        {recommendations?.suggested_patterns && recommendations.suggested_patterns.length > 0 && (
          <div className="mt-6">
            <h3 className="font-bold text-gray-900 mb-3">Suggested Patterns to Try</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {recommendations.suggested_patterns.slice(0, 4).map((pattern, index) => (
                <div key={index} className="p-4 bg-green-50 rounded-lg border border-green-200">
                  <div className="flex justify-between items-start mb-2">
                    <span className="badge badge-green">#{index + 1} Recommended</span>
                    <span className="text-sm text-green-600 font-bold">
                      {(pattern.expected_viral_score * 100).toFixed(0)}% viral
                    </span>
                  </div>
                  <div className="text-sm space-y-1">
                    <p><span className="text-gray-500">Hook:</span> <span className="capitalize">{pattern.hook_type}</span></p>
                    <p><span className="text-gray-500">Emotion:</span> <span className="capitalize">{pattern.emotion}</span></p>
                    <p><span className="text-gray-500">Pacing:</span> <span className="capitalize">{pattern.pacing}</span></p>
                  </div>
                  <p className="text-xs text-gray-600 mt-2">{pattern.reasoning}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* AI Reasoning */}
      {video.ai_reasoning && (
        <div className="card">
          <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-green-500" />
            AI Analysis
          </h2>
          <p className="text-gray-700 whitespace-pre-wrap">{video.ai_reasoning}</p>
        </div>
      )}
    </div>
  )
}

export default Results
