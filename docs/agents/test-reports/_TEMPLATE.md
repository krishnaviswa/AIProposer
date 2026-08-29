# TR-S-XXX: [Title] — Test report

| Field | Value |
|---|---|
| **Slice** | S-XXX |
| **Author** | Tester |
| **Date** | YYYY-MM-DD |
| **Recommendation** | Ship \| Rework |

---

## Summary

Brief outcome. List blockers if Rework.

---

## AC coverage matrix

| AC# | Description | Type | Test reference | Result |
|---|---|---|---|---|
| 1 | | A / M | | Pass / Fail |
| 2 | | | | |

**Coverage:** X / Y AC mapped

---

## Backend tests

### Added
- `backend/tests/test_*.py::test_name`

### Run output
```
cd backend && python -m pytest tests/test_*.py — [pass/fail summary]
```

---

## Frontend tests

### Added
- `frontend/.../__tests__/*.test.tsx`

### Run output
```
npx jest <path> — [pass/fail summary]
```

---

## Manual / integration

| ID | Check | Result |
|---|---|---|
| M-001 | | Pass / Fail |

---

## Regressions

-

---

## Gaps / rework items

1. AC# — description of failure

---

## Sign-off

- [ ] All AC mapped to tests (A or M)
- [ ] Auth (`401`) and ownership (`404`) tested
- [ ] Money invariant tested (if pricing involved)
- [ ] `docs/ai-touchpoints.md` still matches the code
- [ ] Ready for PM acceptance
