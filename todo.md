Done - Foundation — project structure, config/env handling, DB connection, base models, Alembic migrations set up. Nothing functional yet, but everything else depends on this being right.

Auth — signup, login, email verification, password reset, Google OAuth, JWT + refresh token flow, rate limiting on auth routes.

Content engine — Course, CourseVersion, Topic, Section models and admin CRUD endpoints. No student-facing routes yet, just getting content into the database correctly.

Enrollment & access engine — the state machine: purchase → active, expiry cron, renewal, progress tracking, authorization checks (ownership on every row). This is the piece most likely to have a subtle bug, so it deserves its own isolated review.

Payments — Paystack integration, webhook signature verification, idempotency, wiring a confirmed payment into enrollment creation/renewal. Built after piece 4 exists, since payment success is what triggers enrollment changes.

Assessment & certificates — quiz endpoints (start/submit with the time-limit rule), server-side scoring, certificate issuance on pass.