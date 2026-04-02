import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { supabase } from '../lib/supabase'
import { useState, useEffect } from 'react'
import { protocolAPI } from '../services/apiClient'
import './DashboardPage.css'

export default function DashboardPage() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const [protocols, setProtocols] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user) {
      navigate('/login')
      return
    }
    loadProtocols()
  }, [user, navigate])

  async function loadProtocols() {
    try {
      const data = await protocolAPI.listProtocols()
      setProtocols(data)
    } catch (error) {
      console.error('Failed to load protocols:', error)
    } finally {
      setLoading(false)
    }
  }

  async function handleLogout() {
    await supabase.auth.signOut()
    logout()
    navigate('/login')
  }

  function createNewProtocol() {
    navigate('/editor/new')
  }

  if (!user) return null

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>ReproLab Dashboard</h1>
        <div className="header-actions">
          <span className="user-email">{user.email}</span>
          <button onClick={handleLogout} className="logout-btn">
            Logout
          </button>
        </div>
      </header>

      <main className="dashboard-main">
        <div className="section-header">
          <h2>My Protocols</h2>
          <button onClick={createNewProtocol} className="btn-primary">
            + New Protocol
          </button>
        </div>

        {loading ? (
          <p className="loading">Loading protocols...</p>
        ) : protocols.length === 0 ? (
          <div className="empty-state">
            <p>No protocols yet. Create one to get started!</p>
            <button onClick={createNewProtocol} className="btn-primary">
              Create First Protocol
            </button>
          </div>
        ) : (
          <div className="protocols-grid">
            {protocols.map((protocol) => (
              <div key={protocol.id} className="protocol-card">
                <h3>{protocol.name}</h3>
                <p>{protocol.description}</p>
                <div className="score-badge">
                  Score: {protocol.reproducibility_score?.overall || 'N/A'}
                </div>
                <button
                  onClick={() => navigate(`/editor/${protocol.id}`)}
                  className="btn-secondary"
                >
                  Edit
                </button>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
