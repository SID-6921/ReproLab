import { useParams, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import ProtocolEditor from '../components/ProtocolEditor'
import './ProtocolEditorPage.css'

export default function ProtocolEditorPage() {
  const { protocolId } = useParams()
  const { user } = useAuthStore()
  const navigate = useNavigate()

  if (!user) {
    navigate('/login')
    return null
  }

  return (
    <div className="editor-page">
      <ProtocolEditor protocolId={protocolId} />
    </div>
  )
}
