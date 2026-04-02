import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { protocolAPI } from '../services/apiClient'
import './ProtocolEditor.css'

export default function ProtocolEditor({ protocolId }) {
  const navigate = useNavigate()
  const [protocol, setProtocol] = useState({
    name: '',
    description: '',
    materials: [],
    methods: [],
    constraints: [],
  })
  const [score, setScore] = useState(null)
  const [loading, setLoading] = useState(protocolId !== 'new')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (protocolId && protocolId !== 'new') {
      loadProtocol()
    }
  }, [protocolId])

  useEffect(() => {
    // Debounced scoring
    const timer = setTimeout(() => {
      scoreProtocol()
    }, 500)
    return () => clearTimeout(timer)
  }, [protocol])

  async function loadProtocol() {
    try {
      const data = await protocolAPI.getProtocol(protocolId)
      setProtocol(data)
    } catch (err) {
      setError('Failed to load protocol')
    } finally {
      setLoading(false)
    }
  }

  async function scoreProtocol() {
    try {
      const result = await protocolAPI.scoreProtocol(protocol)
      setScore(result)
    } catch (err) {
      console.error('Scoring error:', err)
    }
  }

  async function handleSave() {
    setSaving(true)
    try {
      if (protocolId === 'new') {
        const result = await protocolAPI.createProtocol(protocol)
        navigate(`/editor/${result.id}`)
      } else {
        await protocolAPI.updateProtocol(protocolId, protocol)
      }
    } catch (err) {
      setError('Failed to save protocol')
    } finally {
      setSaving(false)
    }
  }

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setProtocol((prev) => ({ ...prev, [name]: value }))
  }

  const handleArrayInputChange = (field, index, value) => {
    setProtocol((prev) => ({
      ...prev,
      [field]: prev[field].map((item, i) => (i === index ? value : item)),
    }))
  }

  const addArrayItem = (field) => {
    setProtocol((prev) => ({
      ...prev,
      [field]: [...prev[field], ''],
    }))
  }

  const removeArrayItem = (field, index) => {
    setProtocol((prev) => ({
      ...prev,
      [field]: prev[field].filter((_, i) => i !== index),
    }))
  }

  if (loading) return <div className="editor loading">Loading protocol...</div>

  return (
    <div className="editor">
      <div className="editor-header">
        <div>
          <h1>{protocolId === 'new' ? 'New Protocol' : 'Edit Protocol'}</h1>
          {error && <p className="error">{error}</p>}
        </div>
        <button
          onClick={() => navigate('/dashboard')}
          className="btn-back"
        >
          ← Back
        </button>
      </div>

      <div className="editor-layout">
        <div className="editor-form">
          {/* Basic Information */}
          <section className="form-section">
            <h2>Protocol Information</h2>
            <div className="form-group">
              <label>Protocol Name *</label>
              <input
                type="text"
                name="name"
                value={protocol.name}
                onChange={handleInputChange}
                placeholder="e.g., DNA Extraction Protocol"
                required
              />
            </div>
            <div className="form-group">
              <label>Description</label>
              <textarea
                name="description"
                value={protocol.description}
                onChange={handleInputChange}
                placeholder="Detailed description of the protocol..."
                rows={4}
              />
            </div>
          </section>

          {/* Materials */}
          <section className="form-section">
            <h2>Materials & Reagents</h2>
            <p className="section-hint">List all materials with catalog numbers for traceability</p>
            {protocol.materials.map((material, idx) => (
              <div key={idx} className="array-item">
                <input
                  type="text"
                  value={material}
                  onChange={(e) =>
                    handleArrayInputChange('materials', idx, e.target.value)
                  }
                  placeholder="e.g., Taq polymerase (NEB M0273L)"
                  className="array-input"
                />
                <button
                  onClick={() => removeArrayItem('materials', idx)}
                  className="btn-remove"
                >
                  ✕
                </button>
              </div>
            ))}
            <button
              onClick={() => addArrayItem('materials')}
              className="btn-add"
            >
              + Add Material
            </button>
          </section>

          {/* Methods */}
          <section className="form-section">
            <h2>Experimental Steps</h2>
            <p className="section-hint">Detailed, granular steps for reproducibility</p>
            {protocol.methods.map((method, idx) => (
              <div key={idx} className="array-item">
                <textarea
                  value={method}
                  onChange={(e) =>
                    handleArrayInputChange('methods', idx, e.target.value)
                  }
                  placeholder={`Step ${idx + 1}: Describe the action and parameters...`}
                  className="array-textarea"
                  rows={3}
                />
                <button
                  onClick={() => removeArrayItem('methods', idx)}
                  className="btn-remove"
                >
                  ✕
                </button>
              </div>
            ))}
            <button
              onClick={() => addArrayItem('methods')}
              className="btn-add"
            >
              + Add Step
            </button>
          </section>

          {/* Constraints */}
          <section className="form-section">
            <h2>Constraints & Conditions</h2>
            <p className="section-hint">Environmental and operational constraints</p>
            {protocol.constraints.map((constraint, idx) => (
              <div key={idx} className="array-item">
                <input
                  type="text"
                  value={constraint}
                  onChange={(e) =>
                    handleArrayInputChange('constraints', idx, e.target.value)
                  }
                  placeholder="e.g., Temperature: 37°C ± 2°C"
                  className="array-input"
                />
                <button
                  onClick={() => removeArrayItem('constraints', idx)}
                  className="btn-remove"
                >
                  ✕
                </button>
              </div>
            ))}
            <button
              onClick={() => addArrayItem('constraints')}
              className="btn-add"
            >
              + Add Constraint
            </button>
          </section>

          <div className="form-actions">
            <button
              onClick={handleSave}
              disabled={saving}
              className="btn-save"
            >
              {saving ? 'Saving...' : 'Save Protocol'}
            </button>
          </div>
        </div>

        {/* Scoring Panel */}
        <aside className="score-panel">
          <div className="score-card">
            <h3>Reproducibility Score</h3>
            {score ? (
              <>
                <div className="overall-score">
                  <div className="score-number">{score.overall}</div>
                  <div className="score-label">/ 100</div>
                </div>

                <div className="components">
                  <div className="component">
                    <label>Metadata Completeness</label>
                    <div className="score-bar">
                      <div
                        className="bar-fill"
                        style={{
                          width: `${score.metadata_completeness}%`,
                        }}
                      />
                    </div>
                    <span className="score-value">
                      {score.metadata_completeness}
                    </span>
                  </div>

                  <div className="component">
                    <label>Reagent Traceability</label>
                    <div className="score-bar">
                      <div
                        className="bar-fill"
                        style={{
                          width: `${score.reagent_traceability}%`,
                        }}
                      />
                    </div>
                    <span className="score-value">
                      {score.reagent_traceability}
                    </span>
                  </div>

                  <div className="component">
                    <label>Step Granularity</label>
                    <div className="score-bar">
                      <div
                        className="bar-fill"
                        style={{
                          width: `${score.step_granularity}%`,
                        }}
                      />
                    </div>
                    <span className="score-value">
                      {score.step_granularity}
                    </span>
                  </div>
                </div>

                <div className="weights">
                  <p>
                    <strong>Weights:</strong> 45% metadata • 35% traceability •
                    20% granularity
                  </p>
                </div>
              </>
            ) : (
              <p className="scoring-message">
                Fill in protocol details to see live scoring...
              </p>
            )}
          </div>

          <div className="tips-card">
            <h4>💡 Tips for Better Scores</h4>
            <ul>
              <li>Add catalog numbers to materials</li>
              <li>Break down steps into granular actions</li>
              <li>Include specific temperatures & times</li>
              <li>List environmental constraints</li>
            </ul>
          </div>
        </aside>
      </div>
    </div>
  )
}
