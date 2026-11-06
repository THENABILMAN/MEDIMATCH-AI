import type { Page, Route } from '@playwright/test'
import type {
  AdminBillingCharge,
  AdminDoctor,
  Appointment,
  AuditLog,
  AvailabilitySlot,
  BillingPlan,
  BillingPricing,
  ChatMessage,
  DoctorCredential,
  DoctorProfile,
  Specialty,
  UserProfile,
  UserRole,
  VerificationEvent,
} from '../../src/types'
import { appointmentFor, buildSlots, CRISIS_REPLY, DISCLAIMER, DOCTORS, EMERGENCY_REPLY, SPECIALTIES, USERS } from './fixtures'

const API = 'http://api.test'
const AUTH = 'http://supabase.test/auth/v1'
const STORAGE_KEY = 'sb-supabase-auth-token'
const CORS = { 'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': '*' }

interface Options {
  role?: UserRole
  signedIn?: boolean
  consent?: boolean
  doctorStatus?: DoctorProfile['verification_status']
  emptyDoctorProfile?: boolean
  empty?: boolean
}

function session(user: UserProfile) {
  const body = Buffer.from(JSON.stringify({ sub: user.id, exp: 4102444800 })).toString('base64url')
  return {
    access_token: `eyJhbGciOiJIUzI1NiJ9.${body}.sig`,
    refresh_token: 'refresh',
    token_type: 'bearer',
    expires_in: 3600000,
    expires_at: 4102444800,
    user: { id: user.id, email: user.email, aud: 'authenticated', role: 'authenticated', app_metadata: {}, user_metadata: {} },
  }
}

/** A small stateful stand-in for the API and Supabase Auth. */
export class MockBackend {
  user: UserProfile
  specialties: Specialty[] = structuredClone(SPECIALTIES)
  doctors: DoctorProfile[] = structuredClone(DOCTORS)
  slots: AvailabilitySlot[]
  appointments: Appointment[] = []
  messages: ChatMessage[] = []
  credentials: DoctorCredential[] = []
  auditLogs: AuditLog[] = []
  history: VerificationEvent[] = []
  mine: DoctorProfile
  pending: AdminDoctor[]
  pricing: BillingPricing = { booking_fee_bdt: null, subscription_monthly_bdt: null }
  billingPlan: BillingPlan | null = null
  charges: AdminBillingCharge[] = []
  chips: { label: string }[] = []
  turn = 0
  delayMs = 0

  constructor(private page: Page, private options: Options) {
    this.user = structuredClone(USERS[options.role ?? 'patient'])
    if (options.consent === false) this.user.ai_consent_at = null
    this.slots = options.empty ? [] : this.doctors.flatMap((item) => buildSlots(item.id))
    if (options.empty) this.doctors = []

    this.mine = {
      ...structuredClone(DOCTORS[0]),
      id: 'd0',
      user_id: USERS.doctor.id,
      full_name: USERS.doctor.full_name,
      verification_status: options.doctorStatus ?? 'approved',
    }
    if (options.emptyDoctorProfile) {
      Object.assign(this.mine, { bio: null, qualifications: [], clinic_name: null, consultation_fee: 0, years_experience: 0, specialties: [] })
    }

    this.pending = options.empty
      ? []
      : [
          { ...structuredClone(DOCTORS[1]), id: 'p1', full_name: 'Dr. Jamil Pending', verification_status: 'pending', phone: '+8801711000001', credentials: [
            { id: 'c1', doctor_id: 'p1', file_path: 'u/1111_bmdc_registration.pdf', document_type: 'bmdc_license', uploaded_at: '2026-10-20T04:00:00Z' },
          ] },
          { ...structuredClone(DOCTORS[3]), id: 'p2', full_name: 'Dr. Zubaida Pending', verification_status: 'pending', phone: null, credentials: [] },
          { ...structuredClone(DOCTORS[0]), id: 'p3', full_name: 'Dr. Rafiqul Suspended', verification_status: 'suspended', credentials: [] },
        ]

    this.auditLogs = options.empty
      ? []
      : [
          { id: 'l1', actor_id: USERS.admin.id, action: 'APPROVE_DOCTOR', target_type: 'doctor_profiles', target_id: 'd1', metadata: { old_status: 'pending', new_status: 'approved' }, created_at: '2026-10-28T06:00:00Z' },
          { id: 'l2', actor_id: USERS.patient.id, action: 'APPOINTMENT_BOOKED', target_type: 'appointment', target_id: 'a1', metadata: { slot_id: 's1', doctor_id: 'd1' }, created_at: '2026-10-27T06:00:00Z' },
        ]
    this.history = options.empty
      ? []
      : [
          { action: 'CREATE_DOCTOR_PROFILE', created_at: '2026-09-01T04:00:00Z' },
          { action: 'REJECT_DOCTOR', created_at: '2026-09-03T04:00:00Z', reason: 'The BMDC certificate photo was too blurry to read.' },
          { action: 'APPROVE_DOCTOR', created_at: '2026-09-06T04:00:00Z' },
        ]

    if (!options.empty && this.user.role === 'patient') {
      this.appointments.push(appointmentFor(this.doctors[0], this.slots[1], this.user))
      this.slots[1].is_booked = true
    }
    if (!options.empty && this.user.role === 'doctor') {
      const slot = this.slots[2]
      this.slots.push({ ...slot, id: 'mine-1', doctor_id: 'd0' })
      this.slots.push({ ...this.slots[3], id: 'mine-2', doctor_id: 'd0', is_booked: true })
      this.appointments.push(appointmentFor(this.mine, this.slots[this.slots.length - 1], USERS.patient))
    }
  }

  async install() {
    const { page, options } = this
    if (options.signedIn !== false) {
      await page.addInitScript(
        ([key, value]) => localStorage.setItem(key, value),
        [STORAGE_KEY, JSON.stringify(session(this.user))]
      )
    }
    await page.route(`${AUTH}/**`, (route) => this.handleAuth(route))
    await page.route(`${API}/**`, (route) => this.handleApi(route))
  }

  private async handleAuth(route: Route) {
    const url = route.request().url()
    if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 204, headers: CORS })
    if (url.includes('/token')) return route.fulfill({ json: session(this.user), headers: CORS })
    if (url.includes('/logout')) return route.fulfill({ status: 204, headers: CORS })
    return route.fulfill({ json: session(this.user).user, headers: CORS })
  }

  private async handleApi(route: Route) {
    const request = route.request()
    const url = new URL(request.url())
    const method = request.method()
    if (method === 'OPTIONS') return route.fulfill({ status: 204, headers: CORS })
    if (this.delayMs) await new Promise((resolve) => setTimeout(resolve, this.delayMs))

    const reply = (body: unknown, status = 200) => route.fulfill({ status, json: body, headers: CORS })
    const path = url.pathname
    const isJson = request.headers()['content-type']?.includes('application/json')
    const body = (isJson ? request.postDataJSON() : {}) as Record<string, string>

    if (path === '/me' && method === 'GET') return reply({ ...this.user, doctor_profile: this.user.role === 'doctor' ? this.mine : null })
    if (path === '/me' && method === 'PATCH') {
      if ('ai_consent' in body) this.user.ai_consent_at = body.ai_consent ? new Date().toISOString() : null
      Object.assign(this.user, { full_name: body.full_name ?? this.user.full_name, phone: body.phone ?? this.user.phone })
      return reply(this.user)
    }
    if (path === '/me/conversations') return reply({ conversations_deleted: 1 })
    if (path === '/me') return reply({ message: 'closed' })
    if (path === '/specialties') return reply(this.specialties)

    if (path === '/doctors/search') return reply(this.search(url))
    if (path === '/doctors/me/profile') {
      if (method !== 'GET') {
        const input = request.postDataJSON() as Partial<DoctorProfile> & { specialty_ids: string[] }
        Object.assign(this.mine, input, {
          specialties: this.specialties.filter((item) => input.specialty_ids.includes(item.id)),
          verification_status: 'pending',
        })
      }
      return reply(this.mine)
    }
    if (path === '/doctors/me/credentials') {
      if (method === 'POST') {
        const type = /name="document_type"\r\n\r\n([^\r]+)/.exec(request.postData() ?? '')?.[1] ?? 'bmdc_license'
        const created = { id: `c${this.credentials.length + 10}`, doctor_id: 'd0', file_path: 'u/1111_bmdc.pdf', document_type: type, uploaded_at: new Date().toISOString() }
        this.credentials.push(created)
        return reply(created)
      }
      return reply(this.credentials)
    }
    if (path === '/doctors/me/verification-history') return reply(this.history)
    if (/^\/doctors\/credentials\/.+\/url$/.test(path)) return reply({ url: 'about:blank' })
    if (path === '/doctors/me/slots') {
      if (method === 'POST') {
        const created = { id: `new-${Date.now()}`, doctor_id: 'd0', start_time: body.start_time, end_time: body.end_time, is_booked: false }
        this.slots.push(created)
        return reply(created, 201)
      }
      return reply(this.slots.filter((slot) => slot.doctor_id === 'd0'))
    }
    if (path.startsWith('/doctors/me/slots/')) {
      this.slots = this.slots.filter((slot) => slot.id !== path.split('/').pop())
      return route.fulfill({ status: 204, headers: CORS })
    }
    const doctorSlots = /^\/doctors\/([^/]+)\/slots$/.exec(path)
    if (doctorSlots) return reply(this.slots.filter((slot) => slot.doctor_id === doctorSlots[1] && !slot.is_booked))
    const doctorDetail = /^\/doctors\/([^/]+)$/.exec(path)
    if (doctorDetail) {
      const found = this.doctors.find((item) => item.id === doctorDetail[1])
      return found ? reply(found) : reply({ detail: 'Doctor not found' }, 404)
    }

    if (path === '/chat/conversations') {
      if (method === 'POST') {
        this.messages = [{ id: 'm0', conversation_id: 'conv-1', sender: 'assistant', content: DISCLAIMER, created_at: new Date().toISOString() }]
        return reply(this.conversation(), 201)
      }
      return reply(this.messages.length ? [this.conversation()] : [])
    }
    if (path === '/chat/conversations/conv-1') return reply({ ...this.conversation(), messages: this.messages })
    if (path === '/chat/conversations/conv-1/messages') return reply(this.chat(body.content))

    if (path === '/appointments/me') return reply(this.appointments)
    if (path === '/appointments') {
      const slot = this.slots.find((item) => item.id === body.slot_id)
      if (!slot || slot.is_booked) return reply({ detail: 'This slot has already been booked by another patient' }, 409)
      slot.is_booked = true
      const doctorProfile = this.doctors.find((item) => item.id === slot.doctor_id) ?? this.doctors[0]
      const created = appointmentFor(doctorProfile, slot, this.user)
      this.appointments.push(created)
      return reply(created, 201)
    }
    const appointmentAction = /^\/appointments\/([^/]+)\/(cancel|complete)$/.exec(path)
    if (appointmentAction) {
      const found = this.appointments.find((item) => item.id === appointmentAction[1])
      if (found) found.status = appointmentAction[2] === 'cancel' ? 'cancelled' : 'completed'
      return reply(found)
    }

    if (path === '/admin/doctors') {
      const status = url.searchParams.get('status')
      const all: AdminDoctor[] = [
        ...this.pending,
        ...this.doctors.map((item) => ({ ...item, credentials: [] })),
      ]
      const items = status ? all.filter((item) => item.verification_status === status) : all
      return reply({ items, total: items.length, limit: 25, offset: 0 })
    }
    const decision = /^\/admin\/doctors\/([^/]+)\/(approve|reject|suspend)$/.exec(path)
    if (decision) {
      const found = this.pending.find((item) => item.id === decision[1])
      if (found) found.verification_status = { approve: 'approved', reject: 'rejected', suspend: 'suspended' }[decision[2]] as DoctorProfile['verification_status']
      return reply({ ok: true })
    }
    if (path === '/admin/patients') {
      const items = this.options.empty
        ? []
        : [
            { id: 'pa1', full_name: 'Demo Patient Karim', phone: '+8801710000002', created_at: '2026-09-02T04:00:00Z', appointment_count: 3 },
            { id: 'pa2', full_name: 'Nusrat Jahan', phone: null, created_at: '2026-10-11T04:00:00Z', appointment_count: 0 },
          ]
      return reply({ items, total: items.length, limit: 25, offset: 0 })
    }
    if (path === '/admin/specialties' && method === 'POST') {
      const created = { id: `s${Date.now()}`, name: body.name, description: body.description }
      this.specialties.push(created)
      return reply(created, 201)
    }
    if (path.startsWith('/admin/specialties/')) {
      const id = path.split('/').pop()
      if (method === 'DELETE') this.specialties = this.specialties.filter((item) => item.id !== id)
      return reply({ ok: true })
    }
    if (path === '/billing/pricing') return reply(this.pricing)
    if (path === '/billing/me/plan') {
      this.billingPlan = body.plan as BillingPlan
      if (body.plan === 'subscription' && this.pricing.subscription_monthly_bdt) {
        this.charges.push({
          id: 'c1',
          kind: 'subscription',
          billing_month: '2026-11-01',
          amount_bdt: this.pricing.subscription_monthly_bdt,
          status: 'owed',
          created_at: '2026-11-06T06:00:00Z',
          settled_at: null,
          doctor_id: 'd1',
          doctor_name: 'Dr. Kazi Ahmed',
        })
      }
    }
    if (path.startsWith('/billing/me')) {
      const owed = this.charges.filter((item) => item.status === 'owed')
      return reply({
        plan: this.billingPlan,
        chosen_at: this.billingPlan ? '2026-11-06T06:00:00Z' : null,
        pricing: this.pricing,
        total_owed_bdt: owed.reduce((sum, item) => sum + item.amount_bdt, 0),
        charges: this.charges,
      })
    }
    if (path === '/admin/billing/pricing') {
      this.pricing = body as unknown as BillingPricing
      return reply(this.pricing)
    }
    if (path === '/admin/billing/charges') {
      return reply({ items: this.charges, total: this.charges.length, limit: 25, offset: 0 })
    }
    if (path.startsWith('/admin/billing/charges/')) {
      const charge = this.charges.find((item) => item.id === path.split('/')[4])
      if (!charge) return reply({ detail: 'Charge not found' }, 404)
      charge.status = body.status as AdminBillingCharge['status']
      return reply(charge)
    }
    if (path === '/admin/audit-logs') {
      return reply({ items: this.auditLogs, total: this.auditLogs.length, limit: 25, offset: 0 })
    }

    return reply({ detail: `Unmocked ${method} ${path}` }, 501)
  }

  private conversation() {
    return { id: 'conv-1', patient_id: this.user.id, title: 'Symptom Consultation', created_at: '2026-11-03T08:00:00Z' }
  }

  private search(url: URL) {
    const specialty = url.searchParams.get('specialty')?.toLowerCase()
    const city = url.searchParams.get('city')?.toLowerCase()
    const maxFee = Number(url.searchParams.get('max_fee')) || Infinity
    const items = this.doctors.filter(
      (item) =>
        item.consultation_fee <= maxFee &&
        (!city || item.city.toLowerCase().includes(city)) &&
        (!specialty || item.specialties.some((entry) => entry.name.toLowerCase().includes(specialty)))
    )
    return { items, total: items.length, page: 1, page_size: 10, total_pages: 1 }
  }

  private chat(content: string) {
    const now = new Date().toISOString()
    this.messages.push({ id: `u${this.messages.length}`, conversation_id: 'conv-1', sender: 'patient', content, created_at: now })

    if (/end my life/i.test(content)) {
      return { conversation_id: 'conv-1', assistant_reply: CRISIS_REPLY, current_step: 'emergency_escalated', safety_status: 'emergency', is_emergency: true, recommendations: [], chips: [], safety_kind: 'self_harm' }
    }
    if (/chest pain|can't breathe/i.test(content)) {
      return { conversation_id: 'conv-1', assistant_reply: EMERGENCY_REPLY, current_step: 'emergency_escalated', safety_status: 'emergency', is_emergency: true, recommendations: [], chips: [], safety_kind: 'physical' }
    }

    this.turn += 1
    if (this.turn === 1) {
      return { conversation_id: 'conv-1', assistant_reply: 'How long have you been experiencing these symptoms (e.g. hours, days, weeks)?', current_step: 'ask_followup', safety_status: 'safe', is_emergency: false, recommendations: [], followup_field: 'duration', chips: this.chips }
    }
    const [first, second] = this.doctors
    const recommendations = [first, second].map((item, index) => ({
      ...item,
      match_score: 88 - index * 6,
      available_slots_count: 8,
      soonest_slot: this.slots.find((slot) => slot.doctor_id === item.id && !slot.is_booked)?.start_time,
      match_explanation: `Specializes in Neurology in Dhaka. Has ${item.years_experience} years of clinical experience.`,
    }))
    return {
      conversation_id: 'conv-1',
      assistant_reply: 'Thank you for sharing your symptoms. Based on what you described, I recommend consulting a specialist in **Neurology** in **Dhaka**.',
      current_step: 'completed',
      safety_status: 'safe',
      is_emergency: false,
      recommendations,
    }
  }
}

/** Fails the test if a page makes any request that isn't handled locally or mocked. */
export function trackProblems(page: Page) {
  const problems: string[] = []
  page.on('console', (message) => {
    if (message.type() === 'error') problems.push(`console: ${message.text()}`)
  })
  page.on('pageerror', (error) => problems.push(`pageerror: ${error.message}`))
  page.on('requestfailed', (request) => {
    if (!request.url().startsWith('about:')) problems.push(`failed: ${request.method()} ${request.url()}`)
  })
  page.on('response', (response) => {
    if (response.status() >= 500) problems.push(`status ${response.status()}: ${response.url()}`)
  })
  return problems
}

export async function setup(page: Page, options: Options = {}) {
  await page.route(/^https?:\/\/(?!localhost|api\.test|supabase\.test)/, (route) => route.abort())
  const backend = new MockBackend(page, options)
  await backend.install()
  return backend
}
