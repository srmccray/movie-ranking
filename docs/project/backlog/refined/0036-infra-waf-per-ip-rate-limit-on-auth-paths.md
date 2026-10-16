---
id: '0036'
title: 'infra/lib/movie-ranking-stack.ts: add a CloudFront WAF per-IP rate rule for
  /api/v1/auth/*'
status: Refined
dependencies:
- TASK-0035
governing_adrs:
- ADR-0009
governing_prds:
- PRD-0007
governing_stories:
- US-0010
target_bc: infra
---

# TASK-0036: infra/lib/movie-ranking-stack.ts: add a CloudFront WAF per-IP rate rule for /api/v1/auth/*

## Summary
API Gateway throttling is global per route, so one noisy IP can consume the whole login budget (and lock everyone else out) while still getting through at the allowed rate. Add an AWS WAF web ACL on the CloudFront distribution with a rate-based rule that blocks an IP exceeding a threshold on the auth paths.

Priority: P2. Size: S. Provenance: Filed via the backlog discovery for waves 1-2 on 2026-10-14; evidence re-verified against main at c81de14 before filing.

## Target and Blueprint
- CloudFront-scope WAF resources must be created in `us-east-1`, which is the stack's region (`deploy.yml` `AWS_REGION: us-east-1`). Add `wafv2.CfnWebACL` with `scope: "CLOUDFRONT"`, default action allow, and one rule `AuthRateLimit`: `RateBasedStatement { limit: 100 (per 5 minutes, the AWS default window), aggregateKeyType: IP, scopeDownStatement: ByteMatchStatement on UriPath STARTS_WITH "/api/v1/auth/" }`, action `Block` (returns 403), with CloudWatch metrics enabled.
- Associate it with the distribution (`webAclId` on the `Distribution`, `movie-ranking-stack.ts:166-220`). Start the rule in `Count` mode for one week, check the `AuthRateLimit` metric, then switch to `Block`.
- Cost to state in the PR: about $5 per month per web ACL plus $1 per rule plus $0.60 per million requests (check current AWS pricing). The product owner must accept this before merging.
- Document in `infra/CLAUDE.md` how to read blocked-request samples and how to unblock an IP.

## Notes and Risks
- 100 requests per 5 minutes per IP is generous for humans and low for credential stuffing; tune after the Count period. Shared NATs (offices, mobile carriers) can trip a too-low limit.
- WAF is the only per-client control available here: in-memory limiting in the app is useless on Lambda (each container has its own counters).
- If the cost is not acceptable, close this task as 'superseded' and rely on TASK-0035.

## Dependencies
- TASK-0035 adds the explicit auth routes and the global limits; the per-IP rule complements them and should be tuned against the same measurements.

## Definition of Done
- [ ] `cdk diff` shows a `CLOUDFRONT` web ACL with the rate rule associated with the distribution.
- [ ] After switching to Block, more than the threshold of `POST /api/v1/auth/login` requests from one IP within 5 minutes receive HTTP 403 from CloudFront while a different IP is unaffected.
- [ ] The Count-mode metric review and the cost acceptance are recorded in the PR.
- [ ] Normal sign-in, registration and Google sign-in still work.

```gherkin
Scenario: Login attempts are rate limited per IP
  Given one IP address has sent more login requests in 5 minutes than the configured limit
  When it sends another POST /api/v1/auth/login request
  Then the request is rejected at the edge with HTTP 403
  And requests from other IP addresses are unaffected
```

## INVEST Criteria
- **Independent**: Ordered after TASK-0035 (see Dependencies); otherwise executed in an isolated task branch without modifying the shared backlog (ADR-0005).
- **Negotiable**: File and symbol boundaries in the blueprint are proposals taken from the code as of main at c81de14; the assignee may adjust them if the Definition of Done still holds.
- **Valuable**: Per-client brute-force protection for sign-in; PRD-0007 outcome 7, US-0010.
- **Estimable**: Evidence cites files, symbols and line ranges as of main at c81de14; re-check line numbers before editing.
- **Small**: Small: one focused PR, a few files, well under 500 lines of change.
- **Testable**: HTTP responses observed from two source IPs against the deployed distribution (ADR-0003).
