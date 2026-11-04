import { Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { AIDisclaimer } from '../../components/domain/ai-disclaimer'
import { EmergencyNotice } from '../../components/domain/emergency-notice'
import { VerificationBadge } from '../../components/domain/verification-badge'
import { Avatar } from '../../components/ui/avatar'
import { Badge } from '../../components/ui/badge'
import { Banner } from '../../components/ui/banner'
import { Button } from '../../components/ui/button'
import { Checkbox, RadioGroup, Switch } from '../../components/ui/choice'
import { Combobox } from '../../components/ui/combobox'
import { ConfirmDialog } from '../../components/ui/dialog'
import { EmptyState } from '../../components/ui/empty-state'
import { Field } from '../../components/ui/field'
import { IconButton } from '../../components/ui/icon-button'
import { Input, Textarea } from '../../components/ui/input'
import { Pagination } from '../../components/ui/pagination'
import { Popover } from '../../components/ui/popover'
import { Select } from '../../components/ui/select'
import { Sheet } from '../../components/ui/sheet'
import { Skeleton } from '../../components/ui/skeleton'
import { SortableHeader, Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table'
import { Tabs } from '../../components/ui/tabs'
import { useToast } from '../../components/ui/toast'

const BANGLA_SAMPLE =
  'আমার দুই দিন ধরে মাথা ব্যথা এবং হালকা জ্বর আছে। ঢাকার মিরপুরে একজন যাচাইকৃত নিউরোলজিস্টের সাথে পরামর্শ করতে চাই।'
const OPTIONS = [
  { value: 'a', label: 'Neurology' },
  { value: 'b', label: 'Cardiology' },
  { value: 'c', label: 'General Medicine' },
]
const TYPE_SCALE = ['text-xs', 'text-sm', 'text-md', 'text-lg', 'text-xl', 'text-2xl', 'text-3xl']

function Specimen({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="border-t border-border py-6">
      <h2 className="mb-3 text-lg font-semibold">{title}</h2>
      <div className="flex flex-col items-start gap-3">{children}</div>
    </section>
  )
}

/** Development only: every primitive in every state. Excluded from production builds. */
export default function ComponentsPage() {
  const { toast } = useToast()
  const [dialog, setDialog] = useState(false)
  const [sheet, setSheet] = useState(false)
  const [select, setSelect] = useState('a')
  const [combo, setCombo] = useState('')
  const [page, setPage] = useState(2)
  const [tab, setTab] = useState('one')

  return (
    <div className="page-gutter py-6">
      <h1 className="font-serif text-2xl">Components</h1>

      <Specimen title="Type and Bangla">
        {TYPE_SCALE.map((size) => (
          <p key={size} className={size} lang="bn">
            {BANGLA_SAMPLE}
          </p>
        ))}
      </Specimen>

      <Specimen title="Button">
        <div className="flex flex-wrap gap-2">
          <Button>Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="danger">Danger</Button>
          <Button variant="link">Link</Button>
          <Button disabled>Disabled</Button>
          <Button loading>Loading</Button>
          <Button size="sm">Small</Button>
          <IconButton label="Add" variant="outline">
            <Plus aria-hidden className="size-5" strokeWidth={1.75} />
          </IconButton>
          <IconButton label="Delete" variant="danger">
            <Trash2 aria-hidden className="size-5" strokeWidth={1.75} />
          </IconButton>
        </div>
      </Specimen>

      <Specimen title="Fields">
        <div className="grid w-full max-w-2xl gap-4 md:grid-cols-2">
          <Field label="Default" hint="Helper text">
            {(control) => <Input {...control} />}
          </Field>
          <Field label="Error" error="Enter a valid phone number.">
            {(control) => <Input {...control} defaultValue="017" />}
          </Field>
          <Field label="Disabled">{(control) => <Input {...control} disabled value="Read only" readOnly />}</Field>
          <Field label="Textarea">{(control) => <Textarea {...control} />}</Field>
          <Field label="Select">
            {(control) => <Select id={control.id} value={select} onValueChange={setSelect} options={OPTIONS} />}
          </Field>
          <Field label="Combobox">
            {(control) => (
              <Combobox
                {...control}
                value={combo}
                onValueChange={setCombo}
                options={OPTIONS}
                emptyMessage="No matches"
                clearLabel="Clear"
              />
            )}
          </Field>
        </div>
        <Checkbox label="Checkbox" defaultChecked />
        <Checkbox label="Disabled checkbox" disabled />
        <RadioGroup
          aria-label="Radio"
          defaultValue="one"
          options={[
            { value: 'one', label: 'First option', description: 'With a description' },
            { value: 'two', label: 'Second option' },
          ]}
        />
        <Switch label="Switch" description="With a description" className="w-72" defaultChecked />
      </Specimen>

      <Specimen title="Status">
        <div className="flex flex-wrap items-center gap-2">
          <Badge>Neutral</Badge>
          <Badge tone="primary">Primary</Badge>
          <Badge tone="ai">AI</Badge>
          <Badge tone="success">Success</Badge>
          <Badge tone="warning">Warning</Badge>
          <Badge tone="danger">Danger</Badge>
          <VerificationBadge status="approved" />
          <VerificationBadge status="pending" />
          <VerificationBadge status="rejected" />
          <VerificationBadge status="suspended" />
          <Avatar name="Dr. Tanvir Hasan" />
        </div>
        <Banner title="Information">Something worth knowing.</Banner>
        <Banner tone="warning" title="Warning">
          Something that needs attention.
        </Banner>
        <div className="w-full">
          <EmergencyNotice message="Please call 999 immediately or go to the nearest hospital emergency room." />
        </div>
        <AIDisclaimer />
        <Skeleton className="h-10 w-64" />
        <EmptyState className="w-full" title="No appointments yet" description="Describe your symptoms to find a doctor." />
      </Specimen>

      <Specimen title="Overlays">
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" onClick={() => setDialog(true)}>
            Dialog
          </Button>
          <Button variant="secondary" onClick={() => setSheet(true)}>
            Sheet
          </Button>
          <Button variant="secondary" onClick={() => toast('Your changes were saved.')}>
            Toast
          </Button>
          <Popover trigger={<Button variant="secondary">Popover</Button>}>Popover content</Popover>
        </div>
        <ConfirmDialog
          open={dialog}
          onOpenChange={setDialog}
          title="Cancel your appointment?"
          description="This frees the slot for other patients."
          confirmLabel="Cancel Appointment"
          cancelLabel="Keep Appointment"
          onConfirm={() => setDialog(false)}
        />
        <Sheet open={sheet} onOpenChange={setSheet} title="Sheet">
          Sheet content
        </Sheet>
      </Specimen>

      <Specimen title="Navigation and tables">
        <Tabs
          className="w-full"
          value={tab}
          onValueChange={setTab}
          tabs={[
            { value: 'one', label: 'Upcoming' },
            { value: 'two', label: 'Past' },
          ]}
        >
          Panel content
        </Tabs>
        <div className="w-full">
          <Table caption="Sample table">
            <TableHead>
              <tr>
                <SortableHeader direction="ascending" onSort={() => undefined}>
                  Name
                </SortableHeader>
                <TableHeader className="text-right">Fee</TableHeader>
              </tr>
            </TableHead>
            <TableBody>
              <TableRow>
                <TableCell>Sample row</TableCell>
                <TableCell className="text-right tabular">1,500</TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>
        <div className="w-full">
          <Pagination page={page} pageCount={5} total={120} onPageChange={setPage} />
        </div>
      </Specimen>
    </div>
  )
}
