CREATE TABLE IF NOT EXISTS public.buddy_reminders (
    id uuid PRIMARY KEY,
    device_id text NOT NULL,
    text text NOT NULL CHECK (length(trim(text)) > 0),
    due_at timestamptz NOT NULL,
    status text NOT NULL CHECK (status IN ('PENDING', 'DELIVERED', 'CANCELLED')),
    created_at timestamptz NOT NULL,
    delivered_at timestamptz
);

CREATE INDEX IF NOT EXISTS buddy_reminders_pending_due
ON public.buddy_reminders (status, due_at, created_at);

ALTER TABLE public.buddy_reminders ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.buddy_reminders FROM anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE
ON public.buddy_reminders TO service_role;
