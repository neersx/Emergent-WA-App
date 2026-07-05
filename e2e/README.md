# E2E Test Suite (Playwright)

End-to-end tests for the WhatsApp SaaS Phase 1 MVP. Each test exercises a real
full-stack flow against a running deployment.

## Setup

```bash
cd /app/e2e
yarn install              # or npm install
yarn install:browsers     # downloads Chromium
```

## Run

Against the live preview URL (default):
```bash
yarn test
```

Against a local dev environment:
```bash
BASE_URL=http://localhost:3000 yarn test
```

Headed / UI mode:
```bash
yarn test:headed
yarn test:ui
```

View the HTML report after a run:
```bash
yarn report
```

## Tests included

| File | Covers |
|------|--------|
| `01-marketing.spec.ts` | Home / Pricing / Features / Contact pages |
| `02-auth.spec.ts` | Register, login (seeded demo owner), wrong password |
| `03-mfa.spec.ts` | TOTP MFA enrollment + verification (uses `otplib`) |
| `04-connect-templates.spec.ts` | Mock Embedded Signup + template sync |
| `05-send-simulate.spec.ts` | Send template + simulate delivered webhook + idempotency |
| `06-inbox.spec.ts` | Inbox conversation creation + service-window-gated reply |
| `07-analytics-settings.spec.ts` | Analytics dashboard + Settings page mode display |
| `08-tenant-isolation.spec.ts` | Cross-tenant data isolation |

## CI

A ready-to-use GitHub Actions workflow is included at
`.github/workflows/e2e.yml`. It boots the backend + frontend services and runs
the entire Playwright suite on every push and pull request.

## Conventions

- All interactive elements expose `data-testid` attributes. New components must
  follow this convention so tests stay robust against design changes.
- The seeded demo account (`owner@demo.com` / `Owner123!`) is **auto-reset on
  every backend startup** (MFA disabled, password restored). Tests rely on this
  to start each suite from a clean state.
- Tests run **serially** (workers=1) because they share the demo tenant's DB
  state. Switch to parallel only after introducing per-test tenant isolation.
