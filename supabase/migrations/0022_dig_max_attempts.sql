-- 0022_dig_max_attempts.sql
-- Raise dig_max_attempts 1 → 2 so a dig job survives ONE transient (retryable) failure
-- instead of dead-lettering on the first hiccup. Permanent failures are still NonRetryable
-- (they do not consume attempts), and 0020 reservation-release means a transient-failed
-- attempt RELEASES its reservation rather than billing — so the extra attempt adds resilience,
-- not spend.
--
-- MONEY-PATH SAFETY — cap-soundness invariant (tests/integration/cap-soundness.test.ts:33):
--     dig_est_cents >= ceil(digWorstCents()) * dig_max_attempts
--   digWorstCents() = 23¢ (flash dig, worst case).  dig_est_cents = 150¢ (unchanged).
--     150 >= 23 * 2 = 46   ✓   — 150¢ already covers up to 6 attempts, so NO est change is
--   needed and the daily-cap guarantee is preserved.
--
-- Why summary is NOT bumped here: summary worst = 115¢ and summary_est_cents = 150¢, so
-- summary_max_attempts=2 would require est >= 230 (a 53% larger reservation → lower throughput).
-- That waits for the settle slice, which recalibrates est to actual cost. See
-- docs/roadmap-to-launch.md (Parking Lot → settle slice).
--
-- guardrail_config is the singleton (id = true), seeded `insert default values` in 0011. This
-- updates the row in place; a fresh `supabase db reset` runs 0011 (default 1) then this (→ 2).
-- The column default is also moved to 2 so the schema default matches the intended value.

alter table guardrail_config alter column dig_max_attempts set default 2;
update guardrail_config set dig_max_attempts = 2 where id = true;
