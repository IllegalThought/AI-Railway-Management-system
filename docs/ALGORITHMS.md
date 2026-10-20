# RailOps AI Algorithms

This document describes algorithms that are implemented and covered by the repository tests. No result is precomputed or hardcoded.

## Platform scheduling model

For each train \(i\), a decision selects a platform \(p_i\) and occupancy start \(s_i\). The occupancy end is \(e_i=s_i+d_i\), where \(d_i\) is the planned occupancy duration. The effective earliest start is scheduled arrival plus recorded delay.

Hard constraints require:

1. \(p_i\) is explicitly compatible with train \(i\).
2. The platform is available, is of the required type, and is long enough.
3. \(s_i\) is no earlier than effective arrival and no later than the configured delay limit.
4. \([s_i,e_i)\) lies inside the scheduling horizon and covers minimum dwell.
5. Two trains on the same platform do not overlap after platform clearance is included.

For trains \(i\) and \(j\) assigned to platform \(p\), one ordering must hold:

\[
e_i+c_p \le s_j \quad \text{or} \quad e_j+c_p \le s_i
\]

The CP-SAT objective minimizes priority-weighted delay and changes from the currently applied platform:

\[
\min \sum_i w_i(s_i-a_i) + \lambda [p_i \ne p_i^{previous}]
\]

where higher-priority services receive a larger \(w_i\), and \(\lambda\) is the reassignment penalty.

## First-Come-First-Served

`solve_fcfs` orders trains deterministically by effective arrival, priority, and identifier. It accepts the first domain candidate that remains consistent with earlier choices. FCFS is a baseline, not an optimizer, and a feasible result never carries an optimality claim.

## Custom CSP

`solve_csp` treats each train as a variable and its feasible platform/time candidates as a domain. It uses:

- minimum remaining values (MRV) to choose the next unassigned train;
- recursive backtracking when a candidate makes the remaining problem unsatisfiable;
- forward checking to remove candidates that conflict with the current partial assignment;
- deterministic candidate ordering and a configurable node limit.

The solver reports `FEASIBLE`, `INFEASIBLE`, or `SEARCH_LIMIT`. An independent validator rechecks persisted output rather than trusting the solver status alone.

## OR-Tools CP-SAT

`solve_cp_sat` creates Boolean platform-selection literals, optional occupancy intervals, exactly-one selection constraints, and `NoOverlap` constraints per platform. It uses a bounded wall-clock time. `OPTIMAL` is reported only when OR-Tools returns `OPTIMAL`; `FEASIBLE` means a solution exists but optimality was not proven.

## Independent validation

`validate_assignments` verifies assignment completeness, compatibility, type, length, availability, timing, delay, dwell, horizon, clearance, and overlap independently from all three solvers. Route validation must also succeed before a plan becomes ready or can be applied.

## A* route search and reservations

The directed station graph uses traversal minutes as nonnegative edge costs. The custom A* implementation maintains open candidates and scores

\[
f(n)=g(n)+h(n)
\]

where \(g(n)\) is accumulated traversal time and \(h(n)\) is a scaled Euclidean lower bound derived from node coordinates. The implementation is deterministic and its route cost is tested against NetworkX Dijkstra.

Validation routes each train from entry to platform and platform to exit. It reserves track resource groups and switch nodes over half-open intervals. A conflicting resource is removed and A* retries an alternate path; an unreachable route becomes a validation issue.

## Forward-chaining inference

The inference engine starts with explicit facts such as `PlatformOccupied`, `PlatformCompatible`, `RouteReserved`, `TrackOccupied`, and `ResourceBlocked`. Rules add `MovementAllowed` or `MovementBlocked` until no new facts can be derived. GREEN is emitted only when all allow-rule premises are present; blocked or occupied resources derive RED; incomplete evidence remains YELLOW.

## Dynamic replanning

Incident replanning reads the current applied plan and authoritative simulation minute. Completed assignments and movements whose first reservation has begun are committed. Their assignment and route reservations are copied exactly. Future trains are solved again with the custom CSP, then independently validated and rerouted around closures and committed resources. A revised plan is not applied automatically and stale revisions are rejected.

## Analytics and comparison

FCFS, CSP, and CP-SAT benchmarks load one immutable station snapshot, candidate domains, hard constraints, horizon, preferred assignments, and maximum delay. Every run records scenario identifier, solver status, measured wall-clock time, total and maximum delay, processed assignment count, objective, and explanation. Timing is observational and varies by machine.

## Complexity and limits

- FCFS is greedy and fast but may fail despite a feasible global solution.
- CSP is exponential in the worst case; MRV and forward checking reduce search, and the node limit bounds work.
- CP-SAT is NP-hard in general and is bounded by a time limit.
- A* is approximately \(O((V+E)\log V)\) with a heap, excluding repeated conflict retries.
- Forward chaining terminates because it operates over a finite fact set and only adds facts.

The model uses integer minutes and a synthetic topology. It is decision-support software, not a safety proof.
