import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for adding auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for handling errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Video API
export const videoAPI = {
  // Upload video
  uploadVideo: (formData) => api.post('/api/v1/videos/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),

  // Get all videos
  getVideos: (params) => api.get('/api/v1/videos', { params }),

  // Get video by ID
  getVideo: (id) => api.get(`/api/v1/videos/${id}`),

  // Get video analysis
  getAnalysis: (id) => api.get(`/api/v1/videos/${id}/analysis`),

  // Trigger analysis
  triggerAnalysis: (id) => api.post(`/api/v1/videos/${id}/analyze`),

  // Delete video
  deleteVideo: (id) => api.delete(`/api/v1/videos/${id}`),

  // Get access URL
  getAccessUrl: (id) => api.get(`/api/v1/videos/${id}/access-url`),
}

// Benchmarks API
export const benchmarkAPI = {
  // Get top patterns
  getTopPatterns: (params) => api.get('/api/v1/benchmarks/patterns', { params }),

  // Get all patterns
  getAllPatterns: () => api.get('/api/v1/benchmarks/patterns/all'),

  // Get benchmark videos
  getVideos: (params) => api.get('/api/v1/benchmarks/videos', { params }),

  // Get stats
  getStats: () => api.get('/api/v1/benchmarks/stats'),
}

// Recommendations API
export const recommendationAPI = {
  // Get video recommendations
  getVideoRecommendations: (videoId) => api.get(`/api/v1/recommendations/videos/${videoId}/recommendations`),

  // Get pattern recommendations
  getPatternRecommendations: (params) => api.get('/api/v1/recommendations/patterns', { params }),

  // Compare patterns
  comparePatterns: (params) => api.get('/api/v1/recommendations/compare', { params }),

  // Get trending patterns
  getTrending: (params) => api.get('/api/v1/recommendations/trending', { params }),
}

export default api
