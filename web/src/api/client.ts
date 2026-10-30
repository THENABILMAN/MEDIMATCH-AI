import { supabase } from '../lib/supabase'
import type {
  Appointment,
  AuditLog,
  AvailabilitySlot,
  ChatMessage,
  Conversation,
  DoctorCredential,
  DoctorProfile,
  DoctorRecommendation,
  Specialty,
  UserProfile,
  VerificationStatus,
} from '../types'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token

  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })

  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`
    try {
      const errJson = await res.json()
      errorDetail = errJson.detail || errJson.message || errorDetail
    } catch {
      // ignore
    }
    throw new Error(errorDetail)
  }

  if (res.status === 204) {
    return {} as T
  }

  return res.json()
}

// -----------------------------------------------------------------------------
// Auth & Profile
// -----------------------------------------------------------------------------
export const api = {
  auth: {
    async registerPatient(data: { email: string; password: string; full_name: string; phone?: string }) {
      return request<{ user: UserProfile; message: string }>('/auth/register-patient', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    },
    async registerDoctor(data: { email: string; password: string; full_name: string; phone?: string }) {
      return request<{ user: UserProfile; message: string }>('/auth/register-doctor', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    },
    async login(data: { email: string; password: string }) {
      return request<{ access_token: string; token_type: string; user: UserProfile }>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    },
    async getMe(): Promise<UserProfile> {
      return request<UserProfile>('/me')
    },
    async updateMe(data: Partial<UserProfile>): Promise<UserProfile> {
      return request<UserProfile>('/me', {
        method: 'PATCH',
        body: JSON.stringify(data),
      })
    },
  },

  // ---------------------------------------------------------------------------
  // AI Symptom Chat
  // ---------------------------------------------------------------------------
  chat: {
    async createConversation(title?: string): Promise<Conversation> {
      return request<Conversation>('/chat/conversations', {
        method: 'POST',
        body: JSON.stringify({ title: title || 'Symptom Consultation' }),
      })
    },
    async listConversations(): Promise<Conversation[]> {
      return request<Conversation[]>('/chat/conversations')
    },
    async getConversation(id: string): Promise<Conversation & { messages: ChatMessage[] }> {
      return request<Conversation & { messages: ChatMessage[] }>(`/chat/conversations/${id}`)
    },
    async sendMessage(
      conversationId: string,
      message: string
    ): Promise<{
      conversation_id: string
      user_message: ChatMessage
      assistant_reply: string
      current_step: string
      safety_status: string
      is_emergency: boolean
      search_criteria?: any
      recommendations?: DoctorRecommendation[]
    }> {
      return request(`/chat/conversations/${conversationId}/messages`, {
        method: 'POST',
        body: JSON.stringify({ content: message, message }),
      })
    },
  },

  // ---------------------------------------------------------------------------
  // Specialties (Public)
  // ---------------------------------------------------------------------------
  specialties: {
    async list(): Promise<Specialty[]> {
      try {
        return await request<Specialty[]>('/specialties')
      } catch {
        return await request<Specialty[]>('/doctors/specialties')
      }
    },
  },

  // ---------------------------------------------------------------------------
  // Doctors & Search
  // ---------------------------------------------------------------------------
  doctors: {
    async search(params: {
      specialty?: string
      city?: string
      max_fee?: number
      min_experience?: number
      sort_by?: string
      page?: number
      page_size?: number
    }): Promise<{
      items: DoctorProfile[]
      total: number
      page: number
      page_size: number
      total_pages: number
    }> {
      const sp = new URLSearchParams()
      if (params.specialty) sp.append('specialty', params.specialty)
      if (params.city) sp.append('city', params.city)
      if (params.max_fee !== undefined) sp.append('max_fee', params.max_fee.toString())
      if (params.min_experience !== undefined) sp.append('min_experience', params.min_experience.toString())
      if (params.sort_by) sp.append('sort_by', params.sort_by)
      if (params.page) sp.append('page', params.page.toString())
      if (params.page_size) sp.append('page_size', params.page_size.toString())

      return request(`/doctors/search?${sp.toString()}`)
    },
    async getById(id: string): Promise<DoctorProfile> {
      return request<DoctorProfile>(`/doctors/${id}`)
    },
    async getPublicSlots(doctorId: string): Promise<AvailabilitySlot[]> {
      return request<AvailabilitySlot[]>(`/doctors/${doctorId}/slots`)
    },
    async getMyProfile(): Promise<DoctorProfile> {
      return request<DoctorProfile>('/doctors/me/profile')
    },
    async updateMyProfile(data: {
      bio?: string
      qualifications: string[]
      years_experience: number
      consultation_fee: number
      clinic_name?: string
      city: string
      specialty_ids: string[]
    }): Promise<DoctorProfile> {
      return request<DoctorProfile>('/doctors/me/profile', {
        method: 'PUT',
        body: JSON.stringify(data),
      })
    },
    async uploadCredential(formData: FormData): Promise<DoctorCredential> {
      return request<DoctorCredential>('/doctors/me/credentials', {
        method: 'POST',
        body: formData,
      })
    },
    async getMySlots(includeBooked = true): Promise<AvailabilitySlot[]> {
      return request<AvailabilitySlot[]>(`/doctors/me/slots?include_booked=${includeBooked}`)
    },
    async createSlot(start_time: string, end_time: string): Promise<AvailabilitySlot> {
      return request<AvailabilitySlot>('/doctors/me/slots', {
        method: 'POST',
        body: JSON.stringify({ start_time, end_time }),
      })
    },
    async deleteSlot(slotId: string): Promise<void> {
      return request<void>(`/doctors/me/slots/${slotId}`, {
        method: 'DELETE',
      })
    },
  },

  // ---------------------------------------------------------------------------
  // Appointments
  // ---------------------------------------------------------------------------
  appointments: {
    async book(slotId: string): Promise<Appointment> {
      return request<Appointment>('/appointments', {
        method: 'POST',
        body: JSON.stringify({ slot_id: slotId }),
      })
    },
    async getMy(status?: string): Promise<Appointment[]> {
      const q = status ? `?status=${status}` : ''
      return request<Appointment[]>(`/appointments/me${q}`)
    },
    async cancel(id: string, reason?: string): Promise<Appointment> {
      return request<Appointment>(`/appointments/${id}/cancel`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
      })
    },
    async complete(id: string): Promise<Appointment> {
      return request<Appointment>(`/appointments/${id}/complete`, {
        method: 'POST',
      })
    },
  },

  // ---------------------------------------------------------------------------
  // Admin Portal
  // ---------------------------------------------------------------------------
  admin: {
    async listDoctors(statusFilter?: VerificationStatus, limit = 50, offset = 0): Promise<{
      items: (DoctorProfile & { credentials?: DoctorCredential[] })[]
      total: number
      limit: number
      offset: number
    }> {
      const q = statusFilter ? `status=${statusFilter}&` : ''
      return request(`/admin/doctors?${q}limit=${limit}&offset=${offset}`)
    },
    async approveDoctor(doctorId: string, reason?: string): Promise<DoctorProfile> {
      return request<DoctorProfile>(`/admin/doctors/${doctorId}/approve`, {
        method: 'POST',
        body: JSON.stringify({ reason: reason || 'Application verified and approved by administrator' }),
      })
    },
    async rejectDoctor(doctorId: string, reason: string): Promise<DoctorProfile> {
      return request<DoctorProfile>(`/admin/doctors/${doctorId}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
      })
    },
    async suspendDoctor(doctorId: string, reason: string): Promise<DoctorProfile> {
      return request<DoctorProfile>(`/admin/doctors/${doctorId}/suspend`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
      })
    },
    async listSpecialties(): Promise<Specialty[]> {
      return request<Specialty[]>('/admin/specialties')
    },
    async createSpecialty(data: { name: string; description?: string }): Promise<Specialty> {
      return request<Specialty>('/admin/specialties', {
        method: 'POST',
        body: JSON.stringify(data),
      })
    },
    async updateSpecialty(id: string, data: { name: string; description?: string }): Promise<Specialty> {
      return request<Specialty>(`/admin/specialties/${id}`, {
        method: 'PUT',
        body: JSON.stringify(data),
      })
    },
    async deleteSpecialty(id: string): Promise<void> {
      return request<void>(`/admin/specialties/${id}`, {
        method: 'DELETE',
      })
    },
    async listAuditLogs(limit = 50, offset = 0): Promise<{
      items: AuditLog[]
      total: number
      limit: number
      offset: number
    }> {
      return request(`/admin/audit-logs?limit=${limit}&offset=${offset}`)
    },
  },
}

