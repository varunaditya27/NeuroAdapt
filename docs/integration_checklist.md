# Integration Checklist

## Owners and Dependencies

- Backend + Quantum core: Sudarshan
- Frontend telemetry + action polling: Prarthana
- Gen engine + compose: Varun

Required dependencies before full run:
- Redis and Postgres reachable
- Backend running with /api/state, /api/action, /api/feedback
- Frontend Observer posting state and ContentRenderer polling action
- Gen engine running and reachable by backend or frontend integration path

## Acceptance Checks

- Backend health returns ok and reports redis connected.
- Observer posts state vectors every 30 seconds with expected field names.
- Redis key state:<session_id> updates with TTL around 300 seconds.
- /api/action returns action_id, confidence, gated; latency < 200 ms.
- Gen engine triggers only when gated is false.
- /api/feedback writes replay_buffer rows in Postgres with correct schema.

## Integration Steps

1) Validate backend core services
- Confirm /api/health returns status ok and redis connected.
- Confirm /api/state accepts a valid payload and stores Redis state.

2) Validate action gating
- Call /api/action for the same session_id.
- Verify confidence threshold behavior (gated true below threshold).

3) Validate frontend loop
- Observer posts state every 30 seconds.
- ContentRenderer polls /api/action and renders expected format.

4) Validate feedback write
- Frontend posts /api/feedback with event data.
- Confirm replay_buffer row inserted and reward returned.

5) Validate full pipeline
- Run a full session end-to-end and verify:
  - Redis state updates
  - Action latency meets target
  - Gating prevents gen engine calls when low confidence
  - Feedback writes to Postgres

## Evidence to Capture

- API response samples for /api/state, /api/action, /api/feedback
- Redis key TTL screenshot or CLI output
- Postgres replay_buffer row sample
- Latency timings for /api/action
- W&B run links or exported plots
