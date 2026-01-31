import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Video, Upload, TrendingUp, Clock, CheckCircle, XCircle, Loader2, Eye } from 'lucide-react'
import { videoAPI } from '../services/api'

const Dashboard = () => {
  const navigate = useNavigate()
  const [videos, setVideos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchVideos()
  }, [])

  const fetchVideos = async () => {
    try {
      const { data } = await videoAPI.getVideos({ limit: 10 })
      setVideos(data.items || [])
    } catch (err) {
      setError('Failed to load videos')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadge = (status) => {
    switch (status) {
      case 'completed':
        return <span className="badge badge-green"><CheckCircle className="w-3 h-3 mr-1" /> Analyzed</span>
      case 'processing':
        return <span className="badge badge-yellow"><Loader2 className="w-3 h-3 mr-1 animate-spin" /> Processing</span>
      case 'pending':
        return <span className="badge badge-blue"><Clock className="w-3 h-3 mr-1" /> Pending</span>
      case 'failed':
        return <span className="badge badge-red"><XCircle className="w-3 h-3 mr-1" /> Failed</span>
      default:
        return <span className="badge">{status}</span>
    }
  }

  const getViralBadge = (probability) => {
    if (probability >= 0.6) {
      return <span className="badge badge-green">High Viral Potential</span>
    } else if (probability >= 0.4) {
      return <span className="badge badge-yellow">Medium Potential</span>
    } else {
      return <span className="badge badge-red">Low Potential</span>
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-2 text-gray-600">
            Your video analysis overview
          </p>
        </div>
        <Link to="/upload" className="btn btn-primary">
          <Upload className="w-4 h-4 mr-2" />
          Upload Video
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-blue-100 rounded-lg">
              <Video className="w-6 h-6 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Total Videos</p>
              <p className="text-2xl font-bold">{videos.length}</p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-green-100 rounded-lg">
              <CheckCircle className="w-6 h-6 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Analyzed</p>
              <p className="text-2xl font-bold">
                {videos.filter(v => v.analysis_status === 'completed').length}
              </p>
            </div>
          </div>
        </div>
        <div className="card">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-purple-100 rounded-lg">
              <TrendingUp className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">High Potential</p>
              <p className="text-2xl font-bold">
                {videos.filter(v => v.viral_probability >= 0.6).length}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Video List */}
      <div className="card">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Recent Videos</h2>

        {error && (
          <div className="p-4 bg-red-50 rounded-lg mb-4">
            <p className="text-red-600">{error}</p>
          </div>
        )}

        {videos.length === 0 ? (
          <div className="text-center py-12">
            <Video className="w-16 h-16 mx-auto text-gray-300 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No videos yet</h3>
            <p className="text-gray-500 mb-4">Upload your first video to get started</p>
            <Link to="/upload" className="btn btn-primary">
              <Upload className="w-4 h-4 mr-2" />
              Upload Video
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Name</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Status</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Viral Potential</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Patterns</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Actions</th>
                </tr>
              </thead>
              <tbody>
                {videos.map((video) => (
                  <tr key={video.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4">
                      <div className="font-medium text-gray-900">{video.name}</div>
                      <div className="text-sm text-gray-500">
                        {new Date(video.created_at).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      {getStatusBadge(video.analysis_status)}
                    </td>
                    <td className="py-3 px-4">
                      {video.analysis_status === 'completed' ? (
                        <div>
                          <div className="font-bold text-lg">
                            {(video.viral_probability * 100).toFixed(0)}%
                          </div>
                          {getViralBadge(video.viral_probability)}
                        </div>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      {video.analysis_status === 'completed' ? (
                        <div className="space-y-1 text-sm">
                          <div><span className="text-gray-500">Hook:</span> {video.hook_type}</div>
                          <div><span className="text-gray-500">Emotion:</span> {video.emotion}</div>
                        </div>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <button
                        onClick={() => navigate(`/results/${video.id}`)}
                        className="btn btn-secondary text-sm"
                        disabled={video.analysis_status !== 'completed'}
                      >
                        <Eye className="w-4 h-4 mr-1" />
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default Dashboard
