# Technical Debt Register

Date: 2026-03-09

## 1) High-Value Debt Items

### TD-01 - Scan Endpoint Trust Boundary
- Severity: High
- Area: Security / Architecture
- Current state: `/api/v1/scan` is unauthenticated by design.
- Risk: spoofed attendance events if route is reachable from untrusted networks.
- Recommended action:
  - enforce kiosk network isolation and reverse-proxy ACLs, and/or
  - add explicit kiosk auth model.
- Effort: 2-4 days
- ROI: Very high (payroll integrity protection)

### TD-02 - Runtime Gate Reliability
- Severity: High
- Area: Delivery / Operations
- Current state: release validation depends on local runtime conditions; this run was blocked by environment.
- Recommended action:
  - CI pipeline with deterministic containerized tests and migration gate.
- Effort: 2-3 days
- ROI: Very high (repeatable release confidence)

### TD-03 - Report Endpoint Complexity
- Severity: Medium
- Area: Maintainability
- Current state: large functions in `reports.py` (`absence_report`, `live_stats`, `employee_absence_detail`).
- Recommended action:
  - split into service-layer calculators and reusable helper modules.
- Effort: 3-5 days
- ROI: High (fewer regressions, easier testing)

## 2) Medium Debt Items

### TD-04 - Frontend Inline Script Density
- Current state: large inline scripts in HTML pages (`admin.html`, `reports.html`, `employees.html`).
- Action: move logic into module files with testable units.
- Effort: 3-4 days
- ROI: Medium-high

### TD-05 - Dependency Security Automation
- Current state: no CI-enforced dependency CVE scanning.
- Action: add `pip-audit`/SCA step and fail threshold policy.
- Effort: 0.5-1 day
- ROI: High

### TD-06 - E2E Coverage Gaps
- Current state: good API-focused tests, limited browser-level flow automation.
- Action: add Playwright/Cypress suite for kiosk/admin/report workflows.
- Effort: 2-4 days
- ROI: High

### TD-07 - Inventory Dependency Graph Accuracy
- Current state: reverse usage map generated heuristically (basename search).
- Action: parser/AST-based import graph generation.
- Effort: 1-2 days
- ROI: Medium

## 3) Low Debt Items

### TD-08 - Frontend Boilerplate Duplication
- Current state: repeated head/layout markup in several pages.
- Action: templating/partial strategy.
- Effort: 1-2 days
- ROI: Medium

### TD-09 - Script Ergonomics
- Current state: Windows launcher scripts exist; cross-platform script parity can improve.
- Action: add equivalent `Makefile`/`justfile` tasks and Linux shell wrappers.
- Effort: 0.5-1 day
- ROI: Medium

### TD-10 - Benchmark Evidence
- Current state: performance claims are mostly static reasoning.
- Action: add reproducible benchmark harness and performance budget targets.
- Effort: 1-2 days
- ROI: Medium

## 4) Legacy/Compatibility Debt

### TD-11 - Backward-Compatible Admin Env Aliases
- Current state: both `FIRST_ADMIN_*` and `DEFAULT_ADMIN_*` aliases supported.
- Tradeoff: compatibility vs configuration simplicity.
- Action:
  - keep aliases for one release cycle,
  - deprecate with warnings,
  - remove aliases after migration window.
- Effort: 0.5 day
- ROI: Medium

## 5) Debt Backlog Prioritization

### Next 7 Days
1. TD-01 (scan boundary)
2. TD-02 (runtime gate reliability)
3. TD-05 (dependency security automation)

### Next 30 Days
1. TD-03 (report refactor)
2. TD-06 (E2E coverage)
3. TD-04 (frontend modularization)

### Next Quarter
1. TD-08 (boilerplate reduction)
2. TD-10 (benchmark harness)
3. TD-11 (alias deprecation completion)

## 6) ROI Summary
| Debt ID | Effort | Risk Reduction | ROI |
|---|---|---|---|
| TD-01 | 2-4d | Very high | Very high |
| TD-02 | 2-3d | Very high | Very high |
| TD-03 | 3-5d | High | High |
| TD-05 | 0.5-1d | High | High |
| TD-06 | 2-4d | High | High |


