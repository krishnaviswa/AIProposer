# TP-S-XXX: [Title] — Test plan

| Field | Value |
|---|---|
| **Slice** | S-XXX |
| **Author** | Tester |
| **Date** | YYYY-MM-DD |

---

## Scope

What this plan covers.

---

## Test strategy

| Layer | Tool | Focus |
|---|---|---|
| Backend API | pytest | auth (`401`), ownership (`404`), happy path, errors, money invariant, quota |
| Frontend | Jest + RTL | interactive components, "no Export JSON", watermark on Free |
| Integration | manual | `docker compose up --build` smoke, `/docs` matches routes |

Environment: `AI_PROVIDER=mock`, `PAYMENT_PROVIDER=mock`, `STORAGE=local`, `EMAIL_PROVIDER=mock`.
No live vendors, no Supabase network.

---

## AC → planned tests

| AC# | Test approach | Test ID / file |
|---|---|---|
| 1 | Automated | `backend/tests/test_*.py::test_name` |
| 2 | Manual | M-001 |
| 3 | Automated | `frontend/.../__tests__/*.test.tsx` |

---

## Standing-invariant cases (include when relevant)

| Case | Expected |
|---|---|
| No / invalid JWT | `401` |
| Another user's row | `404` |
| Model returns a price | server overwrites it; saved amount == user's |
| Generate parse-fail | `502`, quota +0, nothing saved |
| Non-allowlisted PATCH key | `422` |
| Duplicate webhook `provider_event_id` | `200` no-op |

---

## Edge cases

-

---

## Manual checklist

- [ ] M-001: …

---

## Environment notes

-
