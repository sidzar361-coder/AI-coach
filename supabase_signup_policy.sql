-- Keep RLS enabled for the signup table.
-- This allows anonymous users to create accounts while still protecting other rows.

ALTER TABLE public."Signup_Data" ENABLE ROW LEVEL SECURITY;

CREATE POLICY "allow_public_signup_insert"
ON public."Signup_Data"
FOR INSERT
WITH CHECK (true);

-- Optional: if you want to be more restrictive, use the anon role check instead.
-- CREATE POLICY "allow_anon_signup_insert"
-- ON public."Signup_Data"
-- FOR INSERT
-- WITH CHECK (auth.role() = 'anon');
