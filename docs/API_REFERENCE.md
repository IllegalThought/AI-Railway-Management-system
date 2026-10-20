# RailOps AI API Reference

Base path: `/api`. Interactive OpenAPI documentation is served at `/docs`; the schema is at `/api/openapi.json`.

## Workspace contract

All operational endpoints except health and scenario listing require:

```http
X-RailOps-Session: <UUID>
```

An unknown valid UUID creates an isolated normal-traffic workspace. The UUID isolates demo data but is not authentication. Missing, malformed, archived, or expired sessions return `INVALID_SESSION`.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | API and database readiness |
| GET, POST | `/trains` | List or create trains |
| GET, PATCH, DELETE | `/trains/{id}` | Read, update, or delete a train |
| GET | `/platforms` | List platforms |
| GET, PATCH | `/platforms/{id}` | Read or update platform availability and constraints |
| GET | `/scenarios` | List deterministic demo scenarios |
| POST | `/scenarios/{key}/restore` | Restore only the active workspace to a scenario |
| GET | `/overview` | Current train, platform, incident, and activity summary |
| POST | `/schedules/generate` | Generate and persist a versioned FCFS, CSP, or CP-SAT plan |
| POST | `/schedules/validate` | Independently validate platform assignments and routes |
| POST | `/schedules/apply` | Apply the latest validated plan version |
| GET | `/schedules/current` | Read the current operational plan |
| GET | `/network/monitor` | Topology, closures, movements, reservations, and inference |
| GET | `/simulation/state` | Materialized backend-owned simulation state |
| POST | `/simulation/control` | Start, pause, step, or reset with optimistic revision |
| GET, POST | `/incidents` | List or create incidents |
| PATCH | `/incidents/{id}` | Change incident lifecycle status |
| POST | `/incidents/replan` | Calculate a committed-state-safe revised plan |
| GET | `/analytics` | Metrics, trends, utilization, benchmarks, and decision evidence |
| POST | `/analytics/benchmarks` | Compare FCFS, CSP, and CP-SAT on one snapshot |

## Important request shapes

Schedule generation accepts `engine` (`fcfs`, `csp`, `cp_sat`), optional horizon bounds, `maximum_delay_minutes`, `search_limit`, and `time_limit_seconds`. Validation and apply require both `plan_id` and `version`.

Simulation control accepts `action`, `expected_revision`, and optional speed `1`, `2`, or `5`. A stale revision returns HTTP 409.

Incident types are `train_arrival_delay`, `train_departure_delay`, `platform_closure`, `track_blockage`, `junction_closure`, and `new_train_request`. New-train incidents also require train details.

## Errors

Errors use one stable envelope:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "details": [{ "field": "engine", "message": "...", "type": "..." }]
  }
}
```

Common statuses are 400 invalid session/input state, 404 record not found, 409 stale or conflicting operation, 413 request too large, 422 schema validation, and 503 database failure. Database details are logged server-side and not returned to clients.

## Data semantics

- Times are integer minutes.
- Occupancy and reservation intervals are half-open: `[start, end)`.
- Plans are versioned and immutable after supersession.
- `solver_status=OPTIMAL` is the only status that proves CP-SAT optimality.
- Analytics are calculated from persisted plans, assignments, incidents, reservations, and simulation state.
