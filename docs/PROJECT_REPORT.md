# RailOps AI Project Report

## Problem statement

Railway station operations require coordinated platform allocation, route availability, timing, incident response, and clear operator explanations. Manual or isolated tools can obscure conflicts and make replanning difficult. RailOps AI explores these problems in a synthetic, non-safety-critical environment using verifiable algorithms and a professional operations interface.

## Objectives

1. Maintain isolated train, platform, topology, plan, incident, and simulation records.
2. Compare a greedy baseline, a custom constraint solver, and CP-SAT on the same modeled state.
3. Validate platform and route constraints independently before application.
4. Model route reservations and explain movement decisions using explicit facts and rules.
5. Simulate incidents and preserve committed movements during replanning.
6. Calculate analytics from persisted operational data rather than hardcoded claims.
7. Deliver a responsive English-language interface and a portable deployment architecture.

## Architecture and technology

The Next.js/TypeScript frontend calls a FastAPI/Pydantic API. Domain services use SQLAlchemy with SQLite locally and PostgreSQL in deployment. Alembic owns schema evolution. Optimization and reasoning are isolated in backend AI modules using custom Python algorithms, OR-Tools, and NetworkX. See `docs/ARCHITECTURE.md` for boundaries and data flow.

## Implementation

Platform scheduling builds feasible time/platform domains from compatibility, availability, physical dimensions, timing, dwell, clearance, horizon, and delay constraints. FCFS greedily selects candidates; the custom CSP uses MRV, backtracking, and forward checking; CP-SAT optimizes optional intervals. Persisted plans pass an independent validator.

The station topology is a directed weighted graph. Custom A* finds routes around closures and reservations, while NetworkX Dijkstra checks shortest-path cost. Half-open reservations model track groups and switches. Forward chaining derives movement indications from explicit predicates.

Simulation time is persisted and revision-controlled. Incident replanning locks completed or started movements and re-solves future trains. Analytics aggregate plan assignments, state, incidents, routes, and benchmarks. Decision panels explain platform selection, rejected alternatives, routing evidence, and replanning changes.

## Mathematical formulation

Each train \(i\) selects platform \(p_i\) and start \(s_i\). Compatibility, type, length, availability, timing, dwell, maximum delay, horizon, and pairwise non-overlap are hard constraints. CP-SAT minimizes:

\[
\sum_i w_i(s_i-a_i)+\lambda[p_i\ne p_i^{previous}]
\]

A* minimizes traversal cost using \(f(n)=g(n)+h(n)\), where the geometric heuristic is scaled to remain a lower bound. Full equations and semantics are in `docs/ALGORITHMS.md`.

## Testing and actual results

The test suite covers validation, persistence, migrations, session isolation, scheduling, CP-SAT status handling, A* and reference cost, reservations, forward chaining, simulation, incidents, replanning, analytics, and frontend data mapping. Phase 8 adds a complete API workflow from workspace load through revised-plan analytics plus request-limit and security-header checks.

Measured algorithm results are intentionally not fixed in this report: execution time and schedule outcome depend on scenario state, machine, limits, and solver version. The Performance Analytics page runs and persists a current comparison. A CP-SAT result is described as optimal only when its recorded status is `OPTIMAL`.

The final exact test and build counts are recorded in `docs/PROGRESS.md` after release validation.

## Security review

- Production wildcard CORS is rejected.
- Configuration and credentials use environment variables.
- Request schemas and body size are bounded.
- Database errors return safe structured responses.
- API responses use no-store and browser hardening headers.
- Stale plans and simulation revisions are rejected.
- Workspace records are query-scoped and scenario restore cannot reset other sessions.
- No unrestricted global database reset or administration endpoint is exposed.

The UUID workspace contract is isolation, not authentication. A true public multi-user service still needs identity, authorization, rate limiting, server-issued sessions, and operational monitoring.

## Deployment

The frontend is independently deployable to Vercel. The backend is deployable to Render against managed PostgreSQL. Production rollout requires an Alembic upgrade, schema compatibility check, exact HTTPS CORS origin, and frontend API origin. See `docs/DEPLOYMENT.md`.

## Syllabus coverage

The project demonstrates AI problem formulation, heuristic search, constraint satisfaction, knowledge representation, forward chaining, optimization, planning, dynamic replanning, evaluation, responsible claims, and applied deployment. Evidence by Units I–V is in `docs/SYLLABUS_MAPPING.md`.

## Known limitations

- The model is synthetic and uses integer-minute resolution.
- Reservations are exclusive even where topology capacity is greater than one.
- The demo workspace header is not an authentication mechanism.
- Solver work is bounded but not queued across distributed workers.
- Real railway rules, signaling interlocking, rolling-stock constraints, crew, maintenance, passenger connections, and certified safety processes are outside scope.

## Conclusion

RailOps AI integrates genuine scheduling, search, inference, simulation, and analytical workflows behind a consistent operational UI. Its strongest release property is traceability: applied decisions are versioned, independently validated, persisted, measured, and explained from actual modeled evidence.
