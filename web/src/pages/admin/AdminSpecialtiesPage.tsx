import { zodResolver } from '@hookform/resolvers/zod'
import { Pencil, Plus, Trash2 } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { z } from 'zod'
import { useDeleteSpecialty, useSaveSpecialty, useSpecialties } from '../../api/hooks'
import { PageHeader } from '../../components/layout/page-header'
import { Button } from '../../components/ui/button'
import { ConfirmDialog, Dialog } from '../../components/ui/dialog'
import { EmptyState } from '../../components/ui/empty-state'
import { Field } from '../../components/ui/field'
import { IconButton } from '../../components/ui/icon-button'
import { Input, Textarea } from '../../components/ui/input'
import { ErrorState } from '../../components/ui/query-state'
import { Skeleton } from '../../components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { useToast } from '../../components/ui/toast'
import { errorMessage } from '../../lib/errors'
import type { Specialty } from '../../types'

interface SpecialtyValues {
  name: string
  description: string
}

function SpecialtyDialog({ specialty, onClose }: { specialty: Specialty | null; onClose: () => void }) {
  const { t } = useTranslation()
  const { toast } = useToast()
  const save = useSaveSpecialty()
  const schema = useMemo(
    () =>
      z.object({
        name: z.string().trim().min(2, t('specialties.nameRequired')).max(100),
        description: z.string().trim().max(1000),
      }),
    [t]
  )
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SpecialtyValues>({
    resolver: zodResolver(schema),
    mode: 'onBlur',
    defaultValues: { name: specialty?.name ?? '', description: specialty?.description ?? '' },
  })

  async function onSubmit(values: SpecialtyValues) {
    try {
      await save.mutateAsync({ id: specialty?.id, ...values })
      toast(t('specialties.saved', { name: values.name }))
      onClose()
    } catch (error) {
      toast(errorMessage(error, t), 'error')
    }
  }

  return (
    <Dialog
      open
      onOpenChange={(open) => !open && onClose()}
      title={t(specialty ? 'specialties.editTitle' : 'specialties.addTitle')}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button type="submit" form="specialty-form" loading={save.isPending}>
            {t('specialties.save')}
          </Button>
        </>
      }
    >
      <form
        id="specialty-form"
        onSubmit={(event) => void handleSubmit(onSubmit)(event)}
        noValidate
        className="flex flex-col gap-4"
      >
        <Field label={t('specialties.name')} error={errors.name?.message}>
          {(control) => <Input {...control} autoComplete="off" {...register('name')} />}
        </Field>
        <Field label={t('specialties.descriptionField')} optional={t('common.optional')} hint={t('specialties.descriptionHint')}>
          {(control) => <Textarea {...control} {...register('description')} />}
        </Field>
      </form>
    </Dialog>
  )
}

export default function AdminSpecialtiesPage() {
  const { t } = useTranslation()
  const { toast } = useToast()
  const specialties = useSpecialties()
  const remove = useDeleteSpecialty()
  const [editing, setEditing] = useState<Specialty | 'new' | null>(null)
  const [deleting, setDeleting] = useState<Specialty | null>(null)

  async function confirmDelete() {
    if (!deleting) return
    try {
      await remove.mutateAsync(deleting.id)
      toast(t('specialties.deleted', { name: deleting.name }))
      setDeleting(null)
    } catch (error) {
      toast(errorMessage(error, t), 'error')
    }
  }

  return (
    <div className="page-gutter py-4 md:py-6">
      <PageHeader
        title={t('specialties.title')}
        actions={
          <Button onClick={() => setEditing('new')}>
            <Plus aria-hidden className="size-4" strokeWidth={1.75} />
            {t('specialties.add')}
          </Button>
        }
      />
      {specialties.isPending ? (
        <Skeleton className="h-64" />
      ) : specialties.isError ? (
        <ErrorState error={specialties.error} onRetry={() => void specialties.refetch()} />
      ) : specialties.data.length === 0 ? (
        <EmptyState title={t('specialties.emptyTitle')} description={t('specialties.emptyBody')} />
      ) : (
        <Table caption={t('specialties.title')}>
          <TableHead>
            <tr>
              <TableHeader>{t('specialties.name')}</TableHeader>
              <TableHeader className="hidden md:table-cell">{t('specialties.descriptionField')}</TableHeader>
              <TableHeader>
                <span className="sr-only">{t('adminDoctors.actions')}</span>
              </TableHeader>
            </tr>
          </TableHead>
          <TableBody>
            {specialties.data.map((specialty) => (
              <TableRow key={specialty.id}>
                <TableCell className="font-medium whitespace-nowrap">{specialty.name}</TableCell>
                <TableCell className="hidden min-w-48 text-muted md:table-cell">{specialty.description}</TableCell>
                <TableCell>
                  <div className="flex justify-end">
                    <IconButton label={t('specialties.editNamed', { name: specialty.name })} onClick={() => setEditing(specialty)}>
                      <Pencil aria-hidden className="size-4" strokeWidth={1.75} />
                    </IconButton>
                    <IconButton
                      variant="danger"
                      label={t('specialties.deleteNamed', { name: specialty.name })}
                      onClick={() => setDeleting(specialty)}
                    >
                      <Trash2 aria-hidden className="size-4" strokeWidth={1.75} />
                    </IconButton>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {editing && <SpecialtyDialog specialty={editing === 'new' ? null : editing} onClose={() => setEditing(null)} />}
      <ConfirmDialog
        open={Boolean(deleting)}
        onOpenChange={(open) => !open && setDeleting(null)}
        title={t('specialties.deleteTitle', { name: deleting?.name ?? '' })}
        description={t('specialties.deleteBody')}
        confirmLabel={t('specialties.delete')}
        cancelLabel={t('common.goBack')}
        loading={remove.isPending}
        onConfirm={() => void confirmDelete()}
      />
    </div>
  )
}
