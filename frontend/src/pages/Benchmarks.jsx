import { useState, useEffect } from 'react'
import { TrendingUp, Loader2, BarChart3, Zap } from 'lucide-react'
import { benchmarkAPI, recommendationAPI } from '../services/api'

const Benchmarks = () => {
  const [stats, setStats] = useState(null)
  const [topPatterns, setTopPatterns] = useState([])
  const [trending, setTrending] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [statsRes, patternsRes, trendingRes] = await Promise.all([
        benchmarkAPI.getStats(),
        benchmarkAPI.getTopPatterns({ limit: 10 }),
        recommendationAPI.getTrending({ limit: 5 }).catch(() => ({ data: { trending_patterns: [] } }))
      ])
      setStats(statsRes.data)
      setTopPatterns(patternsRes.data)
      setTrending(trendingRes.data?.trending_patterns || [])
    } catch (err) {
      setError('Failed to load benchmark data')
      console.error(err)
    } finally {
      setLoading(false)
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
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Benchmarks</h1>
        <p className="mt-2 text-gray-600">
          Top performing video patterns from benchmark data
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 rounded-lg">
          <p className="text-red-600">{error}</p>
        </div>
      )}

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="card">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-blue-100 rounded-lg">
                <BarChart3 className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Benchmark Videos</p>
                <p className="text-2xl font-bold">{stats.total_benchmarks}</p>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-purple-100 rounded-lg">
                <Zap className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Pattern Combos</p>
                <p className="text-2xl font-bold">{stats.total_patterns}</p>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-green-100 rounded-lg">
                <TrendingUp className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-500">Avg Viral Score</p>
                <p className="text-2xl font-bold">{(stats.avg_viral_score * 100).toFixed(0)}%</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Top Patterns */}
      <div className="card">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Top Performing Patterns</h2>

        {topPatterns.length === 0 ? (
          <p className="text-gray-500">No pattern data available yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Rank</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Hook</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Emotion</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Pacing</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Viral Score</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-500">Sample Size</th>
                </tr>
              </thead>
              <tbody>
                {topPatterns.map((pattern, index) => (
                  <tr key={index} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4">
                      <span className={`badge ${index < 3 ? 'badge-green' : ''}`}>
                        #{index + 1}
                      </span>
                    </td>
                    <td className="py-3 px-4 capitalize">{pattern.hook_type}</td>
                    <td className="py-3 px-4 capitalize">{pattern.emotion}</td>
                    <td className="py-3 px-4 capitalize">{pattern.pacing}</td>
                    <td className="py-3 px-4">
                      <span className={`font-bold ${
                        pattern.expected_viral_score >= 0.6 ? 'text-green-600' :
                        pattern.expected_viral_score >= 0.4 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {(pattern.expected_viral_score * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="py-3 px-4 text-gray-600">{pattern.sample_size}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Trending / Exploration Opportunities */}
      {trending.length > 0 && (
        <div className="card">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Exploration Opportunities</h2>
          <p className="text-gray-600 mb-4">
            Patterns with high potential but needing more data (Thompson Sampling recommendations)
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {trending.map((pattern, index) => (
              <div key={index} className="p-4 bg-purple-50 rounded-lg border border-purple-200">
                <div className="flex justify-between items-start mb-3">
                  <span className="badge badge-blue">Explore</span>
                  <span className="text-sm text-purple-600 font-bold">
                    {(pattern.thompson_score * 100).toFixed(0)}% score
                  </span>
                </div>
                <div className="space-y-1 text-sm">
                  <p><span className="text-gray-500">Hook:</span> <span className="capitalize font-medium">{pattern.hook_type}</span></p>
                  <p><span className="text-gray-500">Emotion:</span> <span className="capitalize font-medium">{pattern.emotion}</span></p>
                  <p><span className="text-gray-500">Pacing:</span> <span className="capitalize font-medium">{pattern.pacing}</span></p>
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Sample size: {pattern.sample_size || 0}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Distribution Charts */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Hook Type Distribution */}
          <div className="card">
            <h3 className="font-bold text-gray-900 mb-4">Hook Type Distribution</h3>
            <div className="space-y-2">
              {Object.entries(stats.hook_type_distribution || {}).map(([type, count]) => (
                <div key={type} className="flex items-center gap-3">
                  <span className="w-32 text-sm capitalize">{type}</span>
                  <div className="flex-1 bg-gray-200 rounded-full h-4">
                    <div
                      className="bg-blue-500 h-4 rounded-full"
                      style={{
                        width: `${(count / stats.total_benchmarks * 100)}%`
                      }}
                    />
                  </div>
                  <span className="text-sm text-gray-500 w-8">{count}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Emotion Distribution */}
          <div className="card">
            <h3 className="font-bold text-gray-900 mb-4">Emotion Distribution</h3>
            <div className="space-y-2">
              {Object.entries(stats.emotion_distribution || {}).map(([emotion, count]) => (
                <div key={emotion} className="flex items-center gap-3">
                  <span className="w-32 text-sm capitalize">{emotion}</span>
                  <div className="flex-1 bg-gray-200 rounded-full h-4">
                    <div
                      className="bg-purple-500 h-4 rounded-full"
                      style={{
                        width: `${(count / stats.total_benchmarks * 100)}%`
                      }}
                    />
                  </div>
                  <span className="text-sm text-gray-500 w-8">{count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Benchmarks
