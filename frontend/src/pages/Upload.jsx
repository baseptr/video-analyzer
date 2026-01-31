import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Upload as UploadIcon, Loader2, CheckCircle } from 'lucide-react'
import { videoAPI } from '../services/api'

const Upload = () => {
  const navigate = useNavigate()
  const [file, setFile] = useState(null)
  const [name, setName] = useState('')
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      setFile(selectedFile)
      if (!name) {
        setName(selectedFile.name.replace(/\.[^/.]+$/, ''))
      }
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) {
      setError('Please select a video file')
      return
    }

    setUploading(true)
    setError(null)
    setResult(null)

    try {
      const formData = new FormData()
      formData.append('video', file)
      formData.append('name', name)
      formData.append('auto_analyze', 'true')

      const { data } = await videoAPI.uploadVideo(formData)
      setResult(data)

      // Reset form
      setFile(null)
      setName('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Upload Video</h1>
        <p className="mt-2 text-gray-600">
          Upload a video to analyze its viral potential
        </p>
      </div>

      {/* Upload Form */}
      <form onSubmit={handleSubmit} className="card space-y-6">
        {/* File Upload */}
        <div>
          <label className="label">Video File</label>
          <div className="mt-1">
            <label
              htmlFor="file-upload"
              className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 px-6 py-10 hover:bg-gray-100"
            >
              {file ? (
                <div className="text-center">
                  <CheckCircle className="mx-auto h-12 w-12 text-green-500" />
                  <p className="mt-2 text-sm font-medium text-gray-900">
                    {file.name}
                  </p>
                  <p className="mt-1 text-xs text-gray-500">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>
              ) : (
                <div className="text-center">
                  <UploadIcon className="mx-auto h-12 w-12 text-gray-400" />
                  <p className="mt-2 text-sm font-medium text-gray-900">
                    Click to upload video
                  </p>
                  <p className="mt-1 text-xs text-gray-500">
                    MP4, MOV up to 100MB
                  </p>
                </div>
              )}
              <input
                id="file-upload"
                name="file-upload"
                type="file"
                className="sr-only"
                accept="video/*"
                onChange={handleFileChange}
                disabled={uploading}
              />
            </label>
          </div>
        </div>

        {/* Video Name */}
        <div>
          <label className="label">Video Name</label>
          <input
            type="text"
            className="input"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter a name for your video"
            required
            disabled={uploading}
          />
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          className="btn btn-primary w-full"
          disabled={uploading || !file}
        >
          {uploading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Uploading & Analyzing...
            </>
          ) : (
            <>
              <UploadIcon className="mr-2 h-4 w-4" />
              Upload & Analyze
            </>
          )}
        </button>
      </form>

      {/* Error Message */}
      {error && (
        <div className="rounded-lg bg-red-50 p-4">
          <p className="text-sm text-red-800">{error}</p>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="card space-y-4 bg-green-50">
          <div className="flex items-center gap-2">
            <CheckCircle className="h-6 w-6 text-green-600" />
            <h3 className="text-lg font-bold text-green-900">
              Upload Complete!
            </h3>
          </div>

          <p className="text-gray-700">
            Your video is being analyzed. This may take a few minutes.
          </p>

          {result.analysis_status === 'completed' && result.viral_probability !== undefined && (
            <div className="space-y-3">
              <div>
                <p className="text-sm font-medium text-gray-700">
                  Viral Probability
                </p>
                <p className="text-2xl font-bold text-green-900">
                  {(result.viral_probability * 100).toFixed(0)}%
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium text-gray-700">Hook Type</p>
                  <p className="text-gray-900">{result.hook_type || '-'}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-700">Emotion</p>
                  <p className="text-gray-900">{result.emotion || '-'}</p>
                </div>
              </div>
            </div>
          )}

          <div className="flex gap-3">
            <button
              onClick={() => navigate(`/results/${result.id}`)}
              className="btn btn-primary"
            >
              View Results
            </button>
            <button
              onClick={() => navigate('/dashboard')}
              className="btn btn-secondary"
            >
              Go to Dashboard
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default Upload
