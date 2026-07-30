---
title: Task Tree Index - AI Care Orchestration Platform (eGFR)
version: 1.1.0
date: 2026-07-29
status: Draft
source: .propel/context/docs/tasks.md
workflow: plan-development-tasks
---

# Task Tree Index

Structure uses Epic -> User Story -> tasks.md.

Master plan:
- .propel/context/docs/tasks.md

Alias epic folders:
- EP-TECH
- EP-001
- EP-DATA-I
- EP-002
- EP-003
- EP-004
- EP-006-I
- EP-006-II
- EP-007
- EP-008-I
- EP-008-11
- EP-008-II
- EP-005
- EP-009
- EP-DATA-II
- EP-CROSS

## Execution Order

Order is dependency-first and should be followed as Epic -> User Story -> Task.

1. EP-TECH
	- US-001: TSK-001
	- US-002: TSK-002
2. EP-DATA-I
	- US-003: TSK-003, TSK-004
	- US-004: TSK-005
   - Canonical pointer: EP-001/tasks.md
3. EP-002
	- US-005: TSK-006, TSK-007
	- US-006: TSK-008
4. EP-003
	- US-007: TSK-009
	- US-008: TSK-010
5. EP-004
	- US-009: TSK-011
	- US-010: TSK-013
	- US-011: TSK-012, TSK-014
6. EP-006-I
	- US-012: TSK-015
7. EP-006-II
	- US-013: TSK-016
8. EP-007
	- US-014: TSK-017
9. EP-008-I
	- US-015: TSK-018
   - Canonical pointer: EP-008-11/tasks.md
10. EP-008-II
	 - US-015: TSK-027 (offline rehearsal and resilience validation)
11. EP-005
	 - US-017: TSK-020, TSK-021
12. EP-009
	 - US-018: TSK-022
13. EP-DATA-II
	 - US-019: TSK-023, TSK-024
14. EP-CROSS (runs continuously once foundation is in place)
	 - US-CROSS: TSK-025, TSK-026

## Parallelization Guidance

- EP-DATA-I can begin after EP-TECH baseline is stable.
- EP-008-I can begin after EP-002 adapters are available.
- EP-005 and EP-009 can run in parallel after EP-004 and EP-007 are stable.
- EP-DATA-II can begin once EP-002 and EP-004 contracts are stable.
