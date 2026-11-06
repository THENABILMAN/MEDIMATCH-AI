import { supabase } from '../lib/supabase'
import type {
  AdminBillingCharge,
  AdminDoctor,
  AdminPatient,
  Appointment,
  AuditLog,
  AvailabilitySlot,
  BillingPlan,
  BillingPricing,
  ChargeStatus,
  ChatReply,
  Conversation,
  ConversationDetail,
  DoctorCredential,
  DoctorProfile,
  DoctorProfileInput,
  DoctorSearchParams,
  DoctorSearchResult,
  MyBilling,
  Page,
  Specialty,
  TableParams,
  UserProfile,
  VerificationEvent,
  VerificationStatus,
} from '../types'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/** A request the server answered with an error. `message` is safe to show. */
export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/** The request never reached the server. */
export class NetworkError extends Error {
  constructor() {
    super('The server could not be reached.')
    this.name = 'NetworkError'
  }
}

function errorDetail(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown } | null)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const first = detail[0] as { msg?: string } | undefined
    if (first?.msg) return first.msg
  }
  return `Request failed with status ${status}`
}

async function authHeader(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...(await authHeader()),
    ...(options.headers as Record<string, string> | undefined),
  }
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }

  let res: Response
  try {
    res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  } catch {
    throw new NetworkError()
  }

  if (!res.ok) {
    const body: unknown = await res.json().catch(() => null)
    throw new ApiError(res.status, errorDetail(body, res.status))
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

function query(params: object): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '') search.set(key, String(value))
  }
  const text = search.toString()
  return text ? `?${text}` : ''
}

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
})

export interface RegisterInput {
  email: string
  password: string
  full_name: string
  phone?: string
}

export const api = {
  auth: {
    registerPatient: (data: RegisterInput) => request<unknown>('/auth/register-patient', json('POST', data)),
    registerDoctor: (data: RegisterInput) => request<unknown>('/auth/register-doctor', json('POST', data)),
    getMe: () => request<UserProfile>('/me'),
    updateMe: (data: { full_name?: string; phone?: string; ai_consent?: boolean }) =>
      request<UserProfile>('/me', json('PATCH', data)),
    deleteChatHistory: () => request<{ conversations_deleted: number }>('/me/conversations', json('DELETE')),
    closeAccount: () => request<{ message: string }>('/me', json('DELETE')),
  },

  chat: {
    createConversation: (title: string) => request<Conversation>('/chat/conversations', json('POST', { title })),
    listConversations: () => request<Conversation[]>('/chat/conversations'),
    getConversation: (id: string) => request<ConversationDetail>(`/chat/conversations/${id}`),
    sendMessage: (conversationId: string, content: string) =>
      request<ChatReply>(`/chat/conversations/${conversationId}/messages`, json('POST', { content })),
  },

  specialties: {
    list: () => request<Specialty[]>('/specialties'),
  },

  doctors: {
    search: (params: DoctorSearchParams) => request<DoctorSearchResult>(`/doctors/search${query(params)}`),
    getById: (id: string) => request<DoctorProfile>(`/doctors/${id}`),
    getPublicSlots: (doctorId: string) => request<AvailabilitySlot[]>(`/doctors/${doctorId}/slots`),
    getMyProfile: () => request<DoctorProfile>('/doctors/me/profile'),
    updateMyProfile: (data: DoctorProfileInput) => request<DoctorProfile>('/doctors/me/profile', json('PUT', data)),
    getMyCredentials: () => request<DoctorCredential[]>('/doctors/me/credentials'),
    getCredentialUrl: (id: string) => request<{ url: string }>(`/doctors/credentials/${id}/url`),
    getVerificationHistory: () => request<VerificationEvent[]>('/doctors/me/verification-history'),
    getMySlots: () => request<AvailabilitySlot[]>('/doctors/me/slots'),
    createSlot: (start_time: string, end_time: string) =>
      request<AvailabilitySlot>('/doctors/me/slots', json('POST', { start_time, end_time })),
    deleteSlot: (slotId: string) => request<void>(`/doctors/me/slots/${slotId}`, json('DELETE')),
  },

  appointments: {
    book: (slotId: string) => request<Appointment>('/appointments', json('POST', { slot_id: slotId })),
    getMy: () => request<Appointment[]>('/appointments/me'),
    cancel: (id: string, reason?: string) =>
      request<Appointment>(`/appointments/${id}/cancel`, json('POST', { reason: reason || null })),
    complete: (id: string) => request<Appointment>(`/appointments/${id}/complete`, json('POST')),
  },

  billing: {
    pricing: () => request<BillingPricing>('/billing/pricing'),
    mine: () => request<MyBilling>('/billing/me'),
    choosePlan: (plan: BillingPlan) => request<MyBilling>('/billing/me/plan', json('PUT', { plan })),
  },
  admin: {
    savePricing: (data: BillingPricing) => request<BillingPricing>('/admin/billing/pricing', json('PUT', data)),
    listCharges: (params: { status?: ChargeStatus; limit: number; offset: number }) =>
      request<Page<AdminBillingCharge>>(`/admin/billing/charges${query(params)}`),
    settleCharge: (id: string, status: ChargeStatus) =>
      request<AdminBillingCharge>(`/admin/billing/charges/${id}/settle`, json('POST', { status })),
    listDoctors: (params: TableParams & { status?: VerificationStatus }) =>
      request<Page<AdminDoctor>>(`/admin/doctors${query(params)}`),
    listPatients: (params: TableParams & { search?: string }) =>
      request<Page<AdminPatient>>(`/admin/patients${query(params)}`),
    approveDoctor: (id: string) => request<unknown>(`/admin/doctors/${id}/approve`, json('POST', {})),
    rejectDoctor: (id: string, reason: string) =>
      request<unknown>(`/admin/doctors/${id}/reject`, json('POST', { reason })),
    suspendDoctor: (id: string, reason: string) =>
      request<unknown>(`/admin/doctors/${id}/suspend`, json('POST', { reason })),
    createSpecialty: (data: { name: string; description?: string }) =>
      request<Specialty>('/admin/specialties', json('POST', data)),
    updateSpecialty: (id: string, data: { name: string; description?: string }) =>
      request<Specialty>(`/admin/specialties/${id}`, json('PUT', data)),
    deleteSpecialty: (id: string) => request<unknown>(`/admin/specialties/${id}`, json('DELETE')),
    listAuditLogs: (params: { limit: number; offset: number; action?: string; date_from?: string; date_to?: string }) =>
      request<Page<AuditLog>>(`/admin/audit-logs${query(params)}`),
  },
}

/** Uploads a credential with XHR, because fetch cannot report upload progress. */
export async function uploadCredential(
  file: File,
  documentType: string,
  onProgress: (percent: number) => void
): Promise<DoctorCredential> {
  const headers = await authHeader()
  const form = new FormData()
  form.append('document_type', documentType)
  form.append('file', file)

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_BASE}/doctors/me/credentials`)
    for (const [name, value] of Object.entries(headers)) xhr.setRequestHeader(name, value)
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100))
    }
    xhr.onerror = () => reject(new NetworkError())
    xhr.onload = () => {
      let body: unknown = null
      try {
        body = JSON.parse(xhr.responseText)
      } catch {
        // A non-JSON failure falls through to the status message
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(body as DoctorCredential)
      else reject(new ApiError(xhr.status, errorDetail(body, xhr.status)))
    }
    xhr.send(form)
  })
}
