import { useMutation, useQuery, useQueries, useQueryClient } from '@tanstack/react-query'
import type {
  BillingPricing,
  ChargeStatus,
  DoctorProfileInput,
  DoctorSearchParams,
  TableParams,
  VerificationStatus,
} from '../types'
import { api } from './client'

export const keys = {
  specialties: ['specialties'] as const,
  doctors: (params: DoctorSearchParams) => ['doctors', params] as const,
  doctor: (id: string) => ['doctor', id] as const,
  doctorSlots: (id: string) => ['doctor', id, 'slots'] as const,
  conversations: ['conversations'] as const,
  conversation: (id: string) => ['conversation', id] as const,
  appointments: ['appointments'] as const,
  myProfile: ['my-doctor-profile'] as const,
  myCredentials: ['my-credentials'] as const,
  mySlots: ['my-slots'] as const,
  verificationHistory: ['verification-history'] as const,
  adminDoctors: ['admin', 'doctors'] as const,
  adminPatients: ['admin', 'patients'] as const,
  auditLogs: ['admin', 'audit-logs'] as const,
  pricing: ['billing', 'pricing'] as const,
  myBilling: ['billing', 'me'] as const,
  adminCharges: ['admin', 'charges'] as const,
}

export function useSpecialties() {
  return useQuery({ queryKey: keys.specialties, queryFn: api.specialties.list, staleTime: 10 * 60 * 1000 })
}

export function useDoctorSearch(params: DoctorSearchParams) {
  return useQuery({ queryKey: keys.doctors(params), queryFn: () => api.doctors.search(params) })
}

export function useDoctor(id: string) {
  return useQuery({ queryKey: keys.doctor(id), queryFn: () => api.doctors.getById(id) })
}

export function useDoctorSlots(id: string) {
  return useQuery({ queryKey: keys.doctorSlots(id), queryFn: () => api.doctors.getPublicSlots(id), staleTime: 0 })
}

export function useDoctorsSlots(ids: string[]) {
  return useQueries({
    queries: ids.map((id) => ({
      queryKey: keys.doctorSlots(id),
      queryFn: () => api.doctors.getPublicSlots(id),
      staleTime: 0,
    })),
  })
}

export function useBookSlot(doctorId: string) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: api.appointments.book,
    onSettled: () => {
      void client.invalidateQueries({ queryKey: keys.doctorSlots(doctorId) })
      void client.invalidateQueries({ queryKey: keys.appointments })
    },
  })
}

export function useAppointments() {
  return useQuery({ queryKey: keys.appointments, queryFn: api.appointments.getMy })
}

export function useCancelAppointment() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason?: string }) => api.appointments.cancel(id, reason),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.appointments }),
  })
}

export function useCompleteAppointment() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: api.appointments.complete,
    onSuccess: () => client.invalidateQueries({ queryKey: keys.appointments }),
  })
}

export function useConversations(enabled = true) {
  return useQuery({ queryKey: keys.conversations, queryFn: api.chat.listConversations, enabled })
}

export function useConversation(id: string | undefined) {
  return useQuery({
    queryKey: keys.conversation(id ?? ''),
    queryFn: () => api.chat.getConversation(id ?? ''),
    enabled: Boolean(id),
    staleTime: 0,
  })
}

export function useMyDoctorProfile() {
  return useQuery({ queryKey: keys.myProfile, queryFn: api.doctors.getMyProfile })
}

export function useUpdateDoctorProfile() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (data: DoctorProfileInput) => api.doctors.updateMyProfile(data),
    onSuccess: (profile) => {
      client.setQueryData(keys.myProfile, profile)
      void client.invalidateQueries({ queryKey: keys.verificationHistory })
    },
  })
}

export function useMyCredentials() {
  return useQuery({ queryKey: keys.myCredentials, queryFn: api.doctors.getMyCredentials })
}

export function useVerificationHistory() {
  return useQuery({ queryKey: keys.verificationHistory, queryFn: api.doctors.getVerificationHistory })
}

export function useMySlots() {
  return useQuery({ queryKey: keys.mySlots, queryFn: api.doctors.getMySlots, staleTime: 0 })
}

export function useCreateSlot() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ start, end }: { start: string; end: string }) => api.doctors.createSlot(start, end),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.mySlots }),
  })
}

export function useDeleteSlot() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: api.doctors.deleteSlot,
    onSuccess: () => client.invalidateQueries({ queryKey: keys.mySlots }),
  })
}

export function useAdminDoctors(params: TableParams & { status?: VerificationStatus }) {
  return useQuery({
    queryKey: [...keys.adminDoctors, params],
    queryFn: () => api.admin.listDoctors(params),
    placeholderData: (previous) => previous,
  })
}

export function useAdminPatients(params: TableParams & { search?: string }) {
  return useQuery({
    queryKey: [...keys.adminPatients, params],
    queryFn: () => api.admin.listPatients(params),
    placeholderData: (previous) => previous,
  })
}

export type DoctorDecision =
  | { doctorId: string; action: 'approve' }
  | { doctorId: string; action: 'reject' | 'suspend'; reason: string }

export function useDoctorDecision() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (decision: DoctorDecision) => {
      if (decision.action === 'approve') return api.admin.approveDoctor(decision.doctorId)
      if (decision.action === 'reject') return api.admin.rejectDoctor(decision.doctorId, decision.reason)
      return api.admin.suspendDoctor(decision.doctorId, decision.reason)
    },
    onSuccess: () => client.invalidateQueries({ queryKey: keys.adminDoctors }),
  })
}

export function useAuditLogs(params: Parameters<typeof api.admin.listAuditLogs>[0]) {
  return useQuery({
    queryKey: [...keys.auditLogs, params],
    queryFn: () => api.admin.listAuditLogs(params),
    placeholderData: (previous) => previous,
  })
}

export function useSaveSpecialty() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id?: string; name: string; description?: string }) =>
      id ? api.admin.updateSpecialty(id, data) : api.admin.createSpecialty(data),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.specialties }),
  })
}

export function useDeleteSpecialty() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: api.admin.deleteSpecialty,
    onSuccess: () => client.invalidateQueries({ queryKey: keys.specialties }),
  })
}

export function usePricing() {
  return useQuery({ queryKey: keys.pricing, queryFn: api.billing.pricing })
}

export function useMyBilling() {
  return useQuery({ queryKey: keys.myBilling, queryFn: api.billing.mine })
}

export function useChooseBillingPlan() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: api.billing.choosePlan,
    onSuccess: (billing) => client.setQueryData(keys.myBilling, billing),
  })
}

export function useSavePricing() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (data: BillingPricing) => api.admin.savePricing(data),
    onSuccess: (pricing) => client.setQueryData(keys.pricing, pricing),
  })
}

export function useAdminCharges(params: { status?: ChargeStatus; limit: number; offset: number }) {
  return useQuery({ queryKey: [...keys.adminCharges, params], queryFn: () => api.admin.listCharges(params) })
}

export function useSettleCharge() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: ChargeStatus }) => api.admin.settleCharge(id, status),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.adminCharges }),
  })
}
