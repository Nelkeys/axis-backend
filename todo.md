Done - Foundation — project structure, config/env handling, DB connection, base models, Alembic migrations set up. Nothing functional yet, but everything else depends on this being right.

Done - Auth — signup, login, email verification, password reset, Google OAuth, JWT + refresh token flow, rate limiting on auth routes.

Done - Content engine — Course, CourseVersion, Topic, Section models and admin CRUD endpoints. No student-facing routes yet, just getting content into the database correctly.

Done - Enrollment & access engine — the state machine: purchase → active, expiry cron, renewal, progress tracking, authorization checks (ownership on every row). This is the piece most likely to have a subtle bug, so it deserves its own isolated review.

Done - Payments — Paystack integration, webhook signature verification, idempotency, wiring a confirmed payment into enrollment creation/renewal. Built after piece 4 exists, since payment success is what triggers enrollment changes.

Done - Assessment & certificates — quiz endpoints (start/submit with the time-limit rule), server-side scoring, certificate issuance on pass.

Done - Wallet / coin balance
Done - My referral code + invitees
Done - Redeem partner invite → become partner
Donr - Partner earnings + payout requests
Done - Admin: generate partner invite codes
Done - Admin: Approve payouts
Done - Coin spend at payment initialize

Done - Wire webhook reward granting — Call grant_referral_reward + coin deduction inside POST /webhooks/paystack on charge.success

Done - Capture referral code during WorkOS callback — Read ?ref=XXXX from /auth/callback URL and save to user.referred_by

Done - Student coin history endpoint — GET /wallet/coin-history returns the signed ledger (earned from referrals, spent at checkout)

Done - Student invitees list — GET /wallet/invitees shows who they referred + their payment status

Done - AnswerLog storage + endpoint — Store every quiz answer attempt ({attempt_id, question_id, selected_index, correct}) so students can review what they got wrong

Done - Admin analytics endpoint — GET /admin/analytics returns attach rate, completion %, referral share, CAC per partner
