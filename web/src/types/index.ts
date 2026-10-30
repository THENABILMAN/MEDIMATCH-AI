export type UserRole = 'patient' | 'doctor' | 'admin'
export type VerificationStatus = 'pending' | 'approved' | 'rejected' | 'suspended'
export type AppointmentStatus = 'booked' | 'cancelled' | 'completed'

export interface UserProfile {
  id: string
  role: UserRole
  full_name: string
  phone?: string | null
  created_at?: string
  updated_at?: string
}

export interface Specialty {
  id: string
  name: string
  description?: string | null
}

export interface DoctorProfile {
  id: string
  user_id: string
  full_name: string
  bio?: string | null
  qualifications: string[]
  years_experience: number
  consultation_fee: number
  clinic_name?: string | null
  city: string
  verification_status: VerificationStatus
  specialties: Specialty[]
  created_at?: string
  sync_status?: string
}

export interface DoctorCredential {
  id: string
  doctor_id: string
  file_path: string
  document_type: string
  uploaded_at: string
}

export interface AvailabilitySlot {
  id: string
  doctor_id: string
  start_time: string
  end_time: string
  is_booked: boolean
  created_at?: string
}

export interface DoctorRecommendation {
  doctor_id: string
  full_name: string
  specialties: string[]
  city: string
  clinic_name?: string | null
  consultation_fee: number
  years_experience: number
  score: number
  match_explanation: string
  next_available_slot?: string | null
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
}

export interface Conversation {
  id: string
  patient_id: string
  title: string
  created_at: string
  updated_at: string
}

export interface AuditLog {
  id: string
  actor_id?: string | null
  action: string
  target_type: string
  target_id?: string | null
  metadata: Record<string, any>
  created_at: string
}

