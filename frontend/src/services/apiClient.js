import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  }
})

export const protocolAPI = {
  async listProtocols() {
    const { data } = await apiClient.get('/protocols')
    return data
  },

  async getProtocol(id) {
    const { data } = await apiClient.get(`/protocols/${id}`)
    return data
  },

  async createProtocol(protocol) {
    const { data } = await apiClient.post('/protocols', protocol)
    return data
  },

  async updateProtocol(id, protocol) {
    const { data } = await apiClient.put(`/protocols/${id}`, protocol)
    return data
  },

  async scoreProtocol(protocolData) {
    const { data } = await apiClient.post('/protocols/score', protocolData)
    return data
  }
}

export default apiClient
