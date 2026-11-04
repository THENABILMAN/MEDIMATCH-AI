import { zodResolver } from '@hookform/resolvers/zod'
import type { TFunction } from 'i18next'
import { useEffect, useMemo } from 'react'
import { Controller, useForm, type UseFormReturn } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { z } from 'zod'
import { useSpecialties } from '../../api/hooks'
import type { DoctorProfile, DoctorProfileInput } from '../../types'
import { Checkbox } from '../ui/choice'
import { Field } from '../ui/field'
import { Input, Textarea } from '../ui/input'
import { Skeleton } from '../ui/skeleton'

export interface DoctorProfileValues {
  city: string
  clinic_name: string
  consultation_fee: number
  years_experience: number
  specialty_ids: string[]
  qualifications: string
  bio: string
}

export const PRACTICE_FIELDS = ['city', 'clinic_name', 'consultation_fee', 'years_experience'] as const
export const CLINICAL_FIELDS = ['specialty_ids', 'qualifications', 'bio'] as const

function buildSchema(t: TFunction) {
  return z.object({
    city: z.string().trim().min(2, t('profile.cityRequired')).max(100),
    clinic_name: z.string().trim().min(2, t('profile.clinicRequired')).max(200),
    consultation_fee: z.number(t('profile.feeRequired')).positive(t('profile.feeRequired')),
    years_experience: z.number(t('profile.experienceRequired')).int().min(0, t('profile.experienceRequired')),
    specialty_ids: z.array(z.string()).min(1, t('profile.specialtyRequired')),
    qualifications: z.string().trim().min(2, t('profile.qualificationsRequired')),
    bio: z.string().trim().min(40, t('profile.bioRequired')).max(2000),
  })
}

export function toProfileInput(values: DoctorProfileValues): DoctorProfileInput {
  return {
    ...values,
    qualifications: values.qualifications
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean),
  }
}

export function useDoctorProfileForm(profile: DoctorProfile | undefined) {
  const { t } = useTranslation()
  const schema = useMemo(() => buildSchema(t), [t])
  const form = useForm<DoctorProfileValues>({ resolver: zodResolver(schema), mode: 'onBlur' })
  const { reset } = form

  useEffect(() => {
    if (!profile) return
    reset({
      city: profile.city,
      clinic_name: profile.clinic_name ?? '',
      // NaN shows an empty field, so a new doctor's fee reads as unset rather than free
      consultation_fee: profile.consultation_fee || Number.NaN,
      years_experience: profile.years_experience,
      specialty_ids: profile.specialties.map((specialty) => specialty.id),
      qualifications: profile.qualifications.join(', '),
      bio: profile.bio ?? '',
    })
  }, [profile, reset])

  return form
}

export function PracticeFields({ form }: { form: UseFormReturn<DoctorProfileValues> }) {
  const { t } = useTranslation()
  const {
    register,
    formState: { errors },
  } = form
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <Field label={t('profile.city')} error={errors.city?.message}>
        {(control) => <Input {...control} autoComplete="address-level2" {...register('city')} />}
      </Field>
      <Field label={t('profile.clinic')} error={errors.clinic_name?.message}>
        {(control) => <Input {...control} autoComplete="organization" {...register('clinic_name')} />}
      </Field>
      <Field label={t('profile.fee')} hint={t('profile.feeHint')} error={errors.consultation_fee?.message}>
        {(control) => (
          <Input
            {...control}
            type="number"
            min={0}
            step={50}
            inputMode="numeric"
            className="tabular"
            {...register('consultation_fee', { valueAsNumber: true })}
          />
        )}
      </Field>
      <Field label={t('profile.experience')} error={errors.years_experience?.message}>
        {(control) => (
          <Input
            {...control}
            type="number"
            min={0}
            inputMode="numeric"
            className="tabular"
            {...register('years_experience', { valueAsNumber: true })}
          />
        )}
      </Field>
    </div>
  )
}

export function ClinicalFields({ form }: { form: UseFormReturn<DoctorProfileValues> }) {
  const { t } = useTranslation()
  const specialties = useSpecialties()
  const {
    control: formControl,
    register,
    formState: { errors },
  } = form
  return (
    <div className="flex flex-col gap-4">
      <fieldset aria-describedby={errors.specialty_ids ? 'specialty-error' : undefined}>
        <legend className="text-sm font-medium">{t('profile.specialties')}</legend>
        {specialties.isPending ? (
          <Skeleton className="mt-2 h-24" />
        ) : (
          <Controller
            control={formControl}
            name="specialty_ids"
            render={({ field }) => (
              <div className="mt-1 grid md:grid-cols-2">
                {(specialties.data ?? []).map((specialty) => (
                  <Checkbox
                    key={specialty.id}
                    label={specialty.name}
                    checked={(field.value ?? []).includes(specialty.id)}
                    onCheckedChange={(checked) =>
                      field.onChange(
                        checked
                          ? [...(field.value ?? []), specialty.id]
                          : (field.value ?? []).filter((id) => id !== specialty.id)
                      )
                    }
                  />
                ))}
              </div>
            )}
          />
        )}
        {errors.specialty_ids && (
          <p id="specialty-error" className="text-sm text-danger">
            {errors.specialty_ids.message}
          </p>
        )}
      </fieldset>
      <Field
        label={t('profile.qualifications')}
        hint={t('profile.qualificationsHint')}
        error={errors.qualifications?.message}
      >
        {(control) => <Input {...control} autoComplete="off" {...register('qualifications')} />}
      </Field>
      <Field label={t('profile.bio')} hint={t('profile.bioHint')} error={errors.bio?.message}>
        {(control) => <Textarea {...control} rows={6} {...register('bio')} />}
      </Field>
    </div>
  )
}
