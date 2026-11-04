export type UserRole = 'patient' | 'doctor' | 'admin'
export type VerificationStatus = 'pending' | 'approved' | 'rejected' | 'suspended'
export type AppointmentStatus = 'booked' | 'cancelled' | 'completed'

export interface Specialty {
  id: string
  name: string
  description?: string | null
}

export interface DoctorProfile {
  id: string
  user_id?: string
  full_name?: string | null
  bio?: string | null
  qualifications: string[]
  years_experience: number
  consultation_fee: number
  clinic_name?: string | null
  city: string
  verification_status: VerificationStatus
  specialties: Specialty[]
  created_at?: string | null
  updated_at?: string | null
}

export interface UserProfile {
  id: string
  email?: string | null
  role: UserRole
  full_name: string
  phone?: string | null
  doctor_profile?: DoctorProfile | null
  ai_consent_at?: string | null
  created_at?: string | null
}

export interface DoctorCredential {
  id: string
  doctor_id: string
  file_path: string
  document_type: string
  uploaded_at: string
}

export interface AdminDoctor extends DoctorProfile {
  phone?: string | null
  credentials: DoctorCredential[]
}

export interface AdminPatient {
  id: string
  full_name: string
  phone?: string | null
  created_at?: string | null
  appointment_count: number
}

export interface AvailabilitySlot {
  id: string
  doctor_id: string
  start_time: string
  end_time: string
  is_booked: boolean
  created_at?: string | null
}

export interface DoctorRecommendation {
  id: string
  user_id: string
  full_name: string
  specialties: Specialty[]
  bio?: string | null
  qualifications: string[]
  years_experience: number
  consultation_fee: number
  clinic_name?: string | null
  city: string
  match_score: number
  available_slots_count: number
  soonest_slot?: string | null
  match_explanation: string
}

export interface Appointment {
  id: string
  patient_id: string
  doctor_id: string
  slot_id?: string | null
  status: AppointmentStatus
  created_at: string
  updated_at?: string | null
  start_time?: string | null
  end_time?: string | null
  doctor?: {
    id: string
    full_name: string
    clinic_name?: string | null
    city: string
    consultation_fee: number
    specialties: string[]
  } | null
  patient?: {
    id: string
    full_name: string
    phone?: string | null
    email?: string | null
  } | null
}

export interface ChatMessage {
  id: string
  conversation_id: string
  sender: 'patient' | 'assistant' | 'system'
  content: string
  created_at: string
  metadata?: {
    is_emergency?: boolean
    recommendations?: DoctorRecommendation[]
  } | null
}

export interface Conversation {
  id: string
  patient_id: string
  title: string
  created_at: string
  updated_at?: string
  initial_message?: string
}

export interface ConversationDetail extends Conversation {
  messages: ChatMessage[]
}

export interface ChatReply {
  conversation_id: string
  assistant_reply: string
  current_step: string
  safety_status: string
  is_emergency: boolean
  recommendations?: DoctorRecommendation[] | null
  followup_field?: string | null
}

export interface AuditLog {
  id: string
  actor_id?: string | null
  action: string
  target_type: string
  target_id?: string | null
  metadata: Record<string, unknown>
  created_at: string
}

export interface VerificationEvent {
  action: string
  created_at: string
  reason?: string | null
}

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface DoctorSearchResult {
  items: DoctorProfile[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface DoctorSearchParams {
  specialty?: string
  city?: string
  max_fee?: number
  min_experience?: number
  sort_by?: string
  page?: number
  page_size?: number
}

export interface DoctorProfileInput {
  bio?: string | null
  qualifications: string[]
  years_experience: number
  consultation_fee: number
  clinic_name?: string | null
  city: string
  specialty_ids: string[]
}

export interface TableParams {
  limit: number
  offset: number
  sort?: string
  descending?: boolean
}
