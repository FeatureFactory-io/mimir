# Consent-gated product analytics

## Contract

Mimir is a long-horizon product-to-market experiment. GA4 records anonymous
behavioural milestones on public pages; Mimir remains authoritative for account
creation and product state. Analytics must not read form values, customer
content, credentials, tokens, or query strings.

## Skeleton and pseudocode

1. Render stable product, experiment, hypothesis, and variant IDs on public
   pages only.
2. Ask for analytics consent before loading the Google tag.
3. On allow, configure GA4 without advertising signals and send a manual,
   query-free page view.
4. Record named CTA, feature, and registration-start events.
5. Emit `sign_up` only when the server-created account success message is
   present.
6. Verify guest, authenticated, form, success, and source-privacy paths.

## Release gates

- Local tests passing does not mean deployed.
- Pipeline deployment does not mean GA4 live data is verified.
- DebugView and Realtime evidence are required before enabling campaigns.
