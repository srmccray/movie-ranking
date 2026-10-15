---
id: 0039
title: 'infra/lib/movie-ranking-stack.ts: set log retention, enable X-Ray, and add
  CloudWatch alarms with SNS email'
status: Complete
dependencies:
- TASK-0037
- TASK-0030
governing_adrs:
- ADR-0009
governing_prds:
- PRD-0007
governing_stories:
- US-0009
target_bc: infra
---

# TASK-0039: infra/lib/movie-ranking-stack.ts: set log retention, enable X-Ray, and add CloudWatch alarms with SNS email

## Summary
The Lambda has default (infinite) log retention, no tracing and no alarms: nobody is told about 5xx errors, throttles or slow requests. Add 30-day log retention, X-Ray active tracing and alarms that email the maintainer.

Priority: P2. Size: S. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- `ApiFunction` (`movie-ranking-stack.ts:70-118`): add `logRetention: logs.RetentionDays.ONE_MONTH` (or an explicit `LogGroup` with that retention) and `tracing: lambda.Tracing.ACTIVE` (adds `AWSXRayDaemonWriteAccess` automatically; verify the deployed role policy in `cdk diff`).
- Alarms (`cloudwatch.Alarm` + `cloudwatch_actions.SnsAction` to an `sns.Topic` with an email subscription taken from a CDK context value `alertEmail`, not committed): Lambda `Errors` >= 1 in 5 minutes; Lambda `Throttles` >= 1; Lambda `Duration` p95 above 20 s (timeout is 30 s, `timeout: cdk.Duration.seconds(30)`); HTTP API `5xx` >= 5 in 5 minutes (`apigatewayv2` metric `5xx` for the API id).
- Optionally set `accessLogSettings` on the default stage to a log group with the same retention.
- Document in `infra/CLAUDE.md`: how to confirm the SNS subscription, how to silence an alarm, and the Logs Insights query for `request_id`.
- Cost: SNS email and the first 10 alarms are free-tier; X-Ray has a free tier of 100,000 traces per month.

## Notes and Risks
- Treat alarm thresholds as starting points; adjust after a week of data.
- The email address is configuration (CDK context or environment), never committed.
- Lambda memory and connection pool tuning is intentionally left for a follow-up once these metrics exist.

## Dependencies
- TASK-0037: the alarms and log queries rely on the structured logs and request ids.
- TASK-0030: a manual `cdk deploy` before the placeholder secrets are removed would reset production configuration.

## Definition of Done
- [ ] `cdk diff` shows the log group retention of 30 days, active tracing and four alarms wired to an SNS topic.
- [ ] After deploy the SNS email subscription is confirmed and a forced test error (alarm `set-alarm-state` or a test request to a failing route) delivers an email.
- [ ] A request produces a trace in the X-Ray console.
- [ ] `infra/CLAUDE.md` documents alarms, retention and the Logs Insights query.

```gherkin
Scenario: Errors page the maintainer
  Given the Lambda Errors alarm is configured with an email subscription
  When the function records an invocation error
  Then the alarm enters the ALARM state
  And an email notification is delivered
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0037, TASK-0030 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Failures and abuse become visible without watching the console; PRD-0007 outcome 5, US-0009.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Small: one focused PR, a few files, well under 500 lines of change.
- **Testable**: Alarm state transitions and delivered notifications are observable on the deployed stack (ADR-0003).
