-- MediMatch AI — Migration 00013: Mental Health Specialties
-- The assistant routes emotional distress to these, not to General Medicine. Fixed ids match
-- backend/scripts/seed.py. An existing specialty with the same name is left as it is.

INSERT INTO public.specialties (id, name, description)
VALUES
    (
        '11111111-0000-0000-0000-000000000004',
        'Psychiatry',
        'Medical assessment and care for mental health, including severe or long-lasting emotional difficulties.'
    ),
    (
        '11111111-0000-0000-0000-000000000005',
        'Clinical Psychology',
        'Talking therapy and psychological assessment for emotional difficulties that affect daily life.'
    ),
    (
        '11111111-0000-0000-0000-000000000006',
        'Counselling',
        'Support for working through loss, relationships, stress and life changes.'
    )
ON CONFLICT (name) DO NOTHING;
