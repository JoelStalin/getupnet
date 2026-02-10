# Agent Master Context Memory
> **Project**: GetUpNet ISP (Odoo 19)
> **Last Updated**: 2026-02-10

## Project Purpose
Full-stack ISP management solution handling:
- Subscriber management (CRM)
- Recurring Billing & Invoicing
- Network Provisioning (MikroTik / ONU)
- Customer Portal (Self-service)
- Fault Ticketing

## Technical Stack
- **Framework**: Odoo 19 (Python 3.10+)
- **Database**: PostgreSQL 15
- **Frontend**: OWL (Odoo Web Library), QWeb
- **Infrastructure**: Docker Compose
- **Key Libraries**: `librouteros` (MikroTik API), `selenium` (Testing)

## User Preferences
- **Language**: User communicates in Spanish.
- **Role**: Developer/Architect.
- **Constraints**: 
  - Keep documentation updated.
  - Follow Odoo best practices.
  - **Testing**: ALWAYS perform validation/tests after completing a task.
  - **Blocking**: Ask for help immediately if blocked or if a mandatory manual operation is required.
  - **Execution**: FINISH THE PLAN without asking for confirmation between steps.

## Context File Index
1. `01_architecture.md`: detailed module structure and data models.
2. `02_development.md`: setup, testing, and deployment workflows.
3. `03_business_rules.md`: key business logic (billing, provisioning).
4. `04_prompts_and_plans.md`: synthesized original master plan and prompt requirements.

## Critical Configuration
- **MikroTik**: Uses `routeros_client` wrapper. Ensure `dry_run=1` for dev.
- **MAC Onboarding**: Requires `isp_core.mac_onboarding_token`.
- **Admin**: User `admin`, Pass `admin` (default dev).
