# Viva Questions and Answers

## System and architecture

1. **What problem does RailOps AI solve?**  
   It models platform allocation, route reservation, incident response, and operational analysis for a synthetic railway station.

2. **Why is it called decision support rather than signaling?**  
   It lacks certified interlocking, fail-safe hardware, formal safety assurance, and real infrastructure integration. It must not control railway assets.

3. **Why separate API, services, and AI modules?**  
   Route handlers manage HTTP contracts, services manage business workflows and persistence, and AI modules remain independently testable.

4. **How is frontend state isolated?**  
   Each browser supplies a UUID in `X-RailOps-Session`; every operational query is scoped to its internal session row.

5. **Is that UUID authentication?**  
   No. It is demo-data isolation. Production identity and authorization remain required.

## Scheduling and optimization

6. **What are the CSP variables and domains?**  
   Each active train is a variable; its domain contains feasible platform, start, end, and delay candidates.

7. **What is MRV?**  
   Minimum remaining values selects the unassigned variable with the fewest currently feasible candidates, exposing failure earlier.

8. **Why use forward checking?**  
   After an assignment, it removes incompatible candidates from remaining domains and backtracks immediately if a domain becomes empty.

9. **How does FCFS differ from CSP?**  
   FCFS greedily accepts the first consistent candidate in arrival order; CSP can revise earlier choices through backtracking.

10. **How is CP-SAT modeled?**  
    It uses selection literals, optional intervals, exactly-one selection, per-platform no-overlap, and a weighted objective.

11. **When can CP-SAT be called optimal?**  
    Only when OR-Tools returns `OPTIMAL`. `FEASIBLE` does not prove optimality.

12. **Why validate solver output independently?**  
    It detects persistence drift, stale inputs, implementation defects, or invalid claims before a plan becomes applicable.

## Routing and inference

13. **Why use A*?**  
    A* combines accumulated traversal time with a lower-bound heuristic to find a least-cost route efficiently.

14. **How is the heuristic kept admissible?**  
    Euclidean distance is scaled so it never exceeds the minimum possible modeled traversal cost.

15. **Why also use NetworkX Dijkstra?**  
    It provides an independent reference for shortest-path cost in tests and validation.

16. **How are route conflicts represented?**  
    Track groups and switch nodes receive half-open time reservations; overlapping exclusive reservations conflict.

17. **What does forward chaining infer?**  
    It derives movement allowed or blocked from explicit platform, compatibility, reservation, occupation, and closure facts.

## Simulation and incidents

18. **Why is the clock backend-owned?**  
    One persisted authoritative clock avoids divergent browser state and survives refreshes.

19. **What prevents stale simulation controls?**  
    Every mutation supplies an expected revision; mismatches return HTTP 409.

20. **How does incident replanning protect active movements?**  
    Completed and started assignments are locked and their route reservations are copied exactly before future trains are recalculated.

21. **Is a revised plan applied automatically?**  
    No. It is independently validated and requires the normal explicit apply action.

## Analytics, testing, and deployment

22. **How is a fair solver benchmark produced?**  
    All engines receive the same loaded station snapshot, hard constraints, domains, horizon, preferred platforms, and delay limit.

23. **Which metrics are actual?**  
    Delays, completed-train count, platform utilization, active conflicts, feasibility, solver time, and replanning impact come from persisted records.

24. **Why can execution time change between runs?**  
    Hardware, process load, solver version, search path, and scenario state affect wall-clock measurements.

25. **How are schema mismatches prevented?**  
    Every model change requires a new Alembic revision, migration tests, upgrade, and `app.database.verify_schema` drift check.

26. **Why PostgreSQL for deployment?**  
    It provides managed concurrency, durability, backups, and operational controls beyond local SQLite.

27. **What security protections exist?**  
    Bounded validation, request-size limits, exact production CORS, safe errors, security headers, no-store API responses, and session-scoped mutations.

28. **What still prevents unrestricted public production use?**  
    Authentication, authorization, rate limiting, server-issued session expiry, abuse protection, and full operations monitoring are not implemented.

29. **What does the Phase 8 integration test prove?**  
    It loads a workspace, reads trains, generates, validates and applies a plan, reads routes, runs simulation controls, creates an incident, replans, applies the revision, and reads analytics and explanations.

30. **What is the main project limitation?**  
    It is a simplified synthetic model and cannot establish the safety or operational correctness required by a real railway.
