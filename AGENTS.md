# RailOps AI Development Rules

These instructions apply to the entire repository.

## Product intent

RailOps AI is a professional, interactive railway operations management platform that uses genuine AI and optimization algorithms. It must look and behave like operational software, not an educational algorithm demonstration.

RailOps AI is a synthetic railway operations simulation. It is not an actual or certified railway signaling, dispatch, or safety system. Product copy and documentation must not imply otherwise.

## User-facing language

All user-facing content must be written in English. This includes navigation, page titles, buttons, form labels, tables, tooltips, notifications, validation errors, dialogs, sample data, generated explanations, documentation, README content, and application metadata. Do not introduce Hindi, regional-language, or mixed-language text.

## Technology baseline

- Frontend: Next.js, TypeScript, Tailwind CSS, shadcn/ui, Lucide, and Recharts.
- Backend: Python, FastAPI, Pydantic, SQLAlchemy, OR-Tools, and NetworkX.
- Data: SQLite for local development and PostgreSQL for deployment.
- Deployment: Vercel for the frontend and Render for the backend.
- Validation: Pytest plus frontend build and type validation.

## Permanent development rules

1. Inspect the existing repository before creating or changing files.
2. Work directly in the current repository; do not create a second nested project.
3. Preserve existing working code and unrelated user changes.
4. Implement only the phase or scope explicitly requested.
5. Do not fabricate AI results or add nonfunctional UI controls.
6. Keep business and domain logic separate from frontend components.
7. Never hardcode secrets or credentials; use environment variables for configuration.
8. Maintain compatibility with GitHub, Vercel, and Render.
9. Add automated tests for important functionality.
10. Run relevant tests and validation before reporting success.
11. Never describe unimplemented or unverified functionality as complete.
12. Apply a consistent, professional design system throughout the application.
13. Keep every user-visible string in English.
14. Treat the platform strictly as a synthetic simulation, never as certified railway signaling software.
15. Keep local and production database configuration portable between SQLite and PostgreSQL.
16. Update `docs/PROGRESS.md` and `docs/ARCHITECTURE.md` when implementation changes project status or architecture.
17. After every SQLAlchemy model change, create or verify the matching Alembic migration, upgrade an existing database copy, and run `python -m app.database.verify_schema` against the intended runtime database. Do not treat an Alembic revision alone as proof of schema compatibility.

