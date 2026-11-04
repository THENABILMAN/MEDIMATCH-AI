import type { Appointment, AvailabilitySlot, DoctorProfile, Specialty, UserProfile, UserRole } from '../../src/types'

// Shaped from backend/scripts/seed.py. Used only by tests and never shipped.
export const SPECIALTIES: Specialty[] = [
  { id: 's1', name: 'Neurology', description: 'Headaches, migraines, seizures and nerve conditions.' },
  { id: 's2', name: 'Cardiology', description: 'Heart and blood vessel conditions.' },
  { id: 's3', name: 'General Medicine', description: 'First assessment for most adult health concerns.' },
]

function doctor(id: string, full_name: string, specialty: Specialty, fee: number, years: number, city: string, clinic: string): DoctorProfile {
  return {
    id,
    user_id: `u-${id}`,
    full_name,
    bio: `Consultant in ${specialty.name.toLowerCase()} with ${years} years of hospital practice, focused on careful assessment and clear follow-up plans for adults.`,
    qualifications: ['MBBS (DMC)', 'FCPS (Medicine)'],
    years_experience: years,
    consultation_fee: fee,
    clinic_name: clinic,
    city,
    verification_status: 'approved',
    specialties: [specialty],
    created_at: '2026-09-01T04:00:00Z',
  }
}

export const DOCTORS: DoctorProfile[] = [
  doctor('d1', 'Dr. Kazi Ahmed', SPECIALTIES[0], 1500, 16, 'Dhaka', 'Square Hospital'),
  doctor('d2', 'Dr. Rubina Akhter', SPECIALTIES[0], 1200, 11, 'Dhaka', 'Labaid Specialized Hospital'),
  doctor('d3', 'Dr. Mahmudul Hasan', SPECIALTIES[2], 800, 9, 'Dhaka', 'Popular Diagnostic Centre'),
  doctor('d4', 'Dr. Samira Rahman', SPECIALTIES[1], 1800, 19, 'Chattogram', 'Chevron Clinical Laboratory'),
]

export function buildSlots(doctorId: string): AvailabilitySlot[] {
  const slots: AvailabilitySlot[] = []
  const base = new Date()
  base.setUTCHours(4, 0, 0, 0)
  for (let day = 1; day <= 3; day += 1) {
    for (let hour = 0; hour < 4; hour += 1) {
      const start = new Date(base.getTime() + day * 86400000 + hour * 3600000)
      slots.push({
        id: `${doctorId}-slot-${day}-${hour}`,
        doctor_id: doctorId,
        start_time: start.toISOString(),
        end_time: new Date(start.getTime() + 30 * 60000).toISOString(),
        is_booked: false,
      })
    }
  }
  return slots
}

export const USERS: Record<UserRole, UserProfile> = {
  patient: {
    id: 'a0000000-0000-0000-0000-000000000002',
    email: 'patient@medimatch.test',
    role: 'patient',
    full_name: 'Demo Patient Karim',
    phone: '+8801710000002',
    ai_consent_at: '2026-10-01T04:00:00Z',
  },
  doctor: {
    id: 'a0000000-0000-0000-0000-000000000003',
    email: 'doctor@medimatch.test',
    role: 'doctor',
    full_name: 'Dr. Tanvir Hasan',
    phone: '+8801710000003',
  },
  admin: {
    id: 'a0000000-0000-0000-0000-000000000001',
    email: 'admin@medimatch.test',
    role: 'admin',
    full_name: 'MediMatch Platform Admin',
  },
}

export const EMERGENCY_REPLY =
  '🚨 EMERGENCY ALERT: Based on your symptoms, this may require immediate emergency medical care.\n\n' +
  'Please call 999 immediately or proceed directly to the nearest hospital emergency room.\n' +
  'Do not wait for an online doctor appointment. Emergency medical personnel should evaluate you without delay.'

export const DISCLAIMER =
  'Hello! I am your MediMatch Assistant.\n\n⚠️ Medical Disclaimer: I am an AI assistant designed solely to help you find qualified medical specialists. I do not provide medical diagnosis, clinical treatment plans, or drug prescriptions. If you are experiencing a life-threatening medical emergency, please call 999 immediately.\n\nPlease describe your symptoms, how long you\'ve had them, and your preferred city or location.'

export function appointmentFor(doctorProfile: DoctorProfile, slot: AvailabilitySlot, patient: UserProfile): Appointment {
  return {
    id: `appt-${slot.id}`,
    patient_id: patient.id,
    doctor_id: doctorProfile.id,
    slot_id: slot.id,
    status: 'booked',
    created_at: new Date().toISOString(),
    start_time: slot.start_time,
    end_time: slot.end_time,
    doctor: {
      id: doctorProfile.id,
      full_name: doctorProfile.full_name ?? '',
      clinic_name: doctorProfile.clinic_name,
      city: doctorProfile.city,
      consultation_fee: doctorProfile.consultation_fee,
      specialties: doctorProfile.specialties.map((item) => item.name),
    },
    patient: { id: patient.id, full_name: patient.full_name, phone: patient.phone },
  }
}
