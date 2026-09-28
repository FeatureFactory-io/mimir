# Change Reconciliation: Realm Top Nav + In-App Sidebar

**Feature ref:** FOB-REALM-NAV-SIDEBAR
**BPE activity:** BPE-08 Process Change Request
**Approved:** 2026-09-28
**Plan:** `docs/plans/FOB_REALM_NAV_SIDEBAR_IMPLEMENTATION_PLAN.md`

The untracked copy of this reconciliation was not on disk when BPE-01 execution continued. This file keeps the approved target and the graduation status.

## Approved target

- Realm bar: FeatureFactory, Mimir, Huginn, Yggdrasil, Heimdall, same tab, plus session chrome on the right.
- App sidebar: Workspace / Methodology / Collaborate. Existing `nav-*` testids.
- Desktop collapse: seam chevron to width 0, `localStorage` key `mm-sidebar-collapsed`.
- Guests see the full sidebar. Home, Teams, and PIPs still login-redirect.
- Mockups at `/mockups/nav/` stay.

## Approval checklist

- [x] Open questions answered
- [x] Target shell accepted
- [x] User approved (2026-09-28)
- [x] In-place spec diffs applied (BPE-08 Step 3)
- [x] BPE-01 plan written (`docs/plans/FOB_REALM_NAV_SIDEBAR_IMPLEMENTATION_PLAN.md`)
- [x] Production shell graduated in `templates/base.html`
