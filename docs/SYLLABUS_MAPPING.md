# Syllabus Mapping: Units I–V

This mapping uses a common five-unit Artificial Intelligence syllabus structure. If an institution uses different unit titles, map the repository evidence by topic rather than renaming implemented capabilities.

| Unit | Typical syllabus coverage | RailOps AI evidence | Demonstrable outcome |
| --- | --- | --- | --- |
| I | AI foundations, intelligent agents, state spaces, problem formulation | Synthetic station state, trains, platforms, incidents, plans, goals, actions, constraints | Explain the environment, state, actions, objective, and limits of the decision-support agent |
| II | Search, heuristic search, constraint satisfaction | Custom A*, Dijkstra reference, CSP variables/domains, backtracking, MRV, forward checking, FCFS baseline | Generate platform plans and routes; compare greedy, systematic, and heuristic methods |
| III | Knowledge representation and reasoning | Explicit predicates, rules, forward chaining, movement facts, evidence explanations | Derive allowed/blocked movement decisions and show the rule evidence |
| IV | Planning and optimization | CP-SAT optional intervals, non-overlap, weighted objective, plan validation/lifecycle, dynamic replanning | Optimize a schedule, validate it, apply it, and revise future work after an incident |
| V | Applied AI systems, evaluation, ethics, deployment | FastAPI/Next.js integration, persisted benchmarks, analytics, session isolation, security review, limitations | Evaluate algorithms on the same scenario and discuss truthful claims and safe deployment |

## Unit I: foundations and formulation

- Observable synthetic state: records, resource availability, simulation minute, reservations, incidents.
- Goals: allocate every active train, satisfy hard constraints, reduce weighted delay and unnecessary reassignment.
- Actions: generate, validate, apply, start, pause, step, report incident, replan.
- Environment qualifications: deterministic data generation, backend-authoritative time, incomplete real-world fidelity.

## Unit II: problem solving and search

- FCFS demonstrates a deterministic greedy baseline.
- CSP demonstrates variable/domain modeling, recursive search, MRV, backtracking, and forward checking.
- A* demonstrates `f=g+h`, admissible heuristic design, closure-aware search, and path reconstruction.
- NetworkX Dijkstra supplies an independent shortest-cost reference.

## Unit III: knowledge and inference

- Facts are restricted predicate tuples, not generated prose.
- Rules infer movement permission or blockage.
- Forward chaining reaches a fixed point over a finite fact set.
- User explanations cite compatibility, occupancy, reservation, and blocked-resource evidence.

## Unit IV: planning and optimization

- CP-SAT models optional platform intervals and per-platform non-overlap.
- The objective combines priority-weighted delay with reassignment cost.
- Independent validation separates solution claims from verification.
- Incident replanning freezes committed movement and revises only safe future decisions.

## Unit V: evaluation and responsible deployment

- Benchmarks run FCFS, CSP, and CP-SAT on identical station state and limits.
- Results retain solver status and wall-clock time; optimality is claimed only for CP-SAT `OPTIMAL`.
- Tests cover algorithms, APIs, migrations, isolation, analytics, and the complete operational workflow.
- Product copy explicitly identifies a synthetic simulation and documents authentication, capacity, resolution, and deployment limitations.
