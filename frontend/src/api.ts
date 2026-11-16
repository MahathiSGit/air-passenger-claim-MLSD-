import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  headers: { 'Content-Type': 'application/json' },
  timeout: 15_000,
})

export type ClaimPayload = {
  complaint: string
  flight_number?: string
  disruption_type?: string
  scheduled_time?: string
  actual_time?: string
}

export type ClaimStatus = 'pending' | 'processing' | 'completed' | 'failed'

export type AcceptedClaim = {
  claim_id: string
  status: 'pending'
  message: string
  created_at: string
}

export type ClaimStatusResponse = {
  claim_id: string
  status: ClaimStatus
  created_at: string
  updated_at: string
  failure_message?: string | null
}

export type WorkflowResult = {
  mode: 'demo' | 'llm'
  claim_analysis: {
    claim_type?: string | null
    flight_number?: string | null
    airline?: string | null
    origin?: string | null
    destination?: string | null
    disruption_type?: string | null
    scheduled_time?: string | null
    actual_time?: string | null
    complaint_summary?: string
    missing_information?: string[]
  }
  regulation_research: {
    relevant_provisions: Array<{ text?: string; citation?: string | null; source?: string; page?: number | null; section?: string | null }>
    conditions?: string[]
    evidence_gaps?: string[]
  }
  entitlement: {
    recommendation: 'pay_as_computed' | 'request_further_evidence' | 'decline' | 'escalate_to_human'
    rationale: string
    compensation_amount?: number | null
    currency?: string | null
    citations?: string[]
    uncertainties?: string[]
  }
  verification: { supported: boolean; flags: string[]; recommendation?: string | null }
  note: string
}

export type ClaimResultResponse = {
  claim_id: string
  status: 'completed'
  created_at: string
  updated_at: string
  result: WorkflowResult
}

export type MetricsResponse = {
  total_claims: number
  pending_claims: number
  processing_claims: number
  completed_claims: number
  failed_claims: number
  escalated_claims: number
  recent_claims: Array<{ claim_id: string; status: ClaimStatus; created_at: string; flight_number?: string | null }>
}

export function getApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (error.response?.data?.error?.message) return error.response.data.error.message
    const validationDetails = error.response?.data?.error?.details
    if (Array.isArray(validationDetails) && validationDetails.length) {
      return validationDetails.map((item: { loc?: unknown[]; msg?: string }) => {
        const field = item.loc?.at(-1)
        return `${typeof field === 'string' ? `${field}: ` : ''}${item.msg || 'invalid value'}`
      }).join(' ')
    }
    if (typeof error.response?.data?.detail === 'string') return error.response.data.detail
    if (error.code === 'ECONNABORTED') return 'The request timed out. Please try again.'
    if (!error.response) return 'Cannot reach the AirClaim API. Check that the backend is running.'
  }
  return 'Something went wrong. Please try again.'
}

export const claimsApi = {
  async submit(payload: ClaimPayload) {
    const { data } = await api.post<AcceptedClaim>('/api/v1/claims', payload)
    return data
  },
  async status(claimId: string) {
    const { data } = await api.get<ClaimStatusResponse>(`/api/v1/claims/${encodeURIComponent(claimId)}`)
    return data
  },
  async result(claimId: string) {
    const { data } = await api.get<ClaimResultResponse>(`/api/v1/claims/${encodeURIComponent(claimId)}/result`)
    return data
  },
  async metrics() {
    const { data } = await api.get<MetricsResponse>('/api/v1/metrics')
    return data
  },
}

