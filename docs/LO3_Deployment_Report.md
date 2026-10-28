# SkyRoute Logistics Ltd: Data Pipeline Deployment, Monitoring and Recovery

**Learning outcome:** LO3  
**Assessment criteria:** P4, P5, P6 and M2  
**Word count:** 924 words, excluding title, metadata, references and figure caption

## Introduction

SkyRoute needs repeatable reporting without losing visibility of errors or exposing shipment data. This report evaluates manual, scheduled and serverless deployment, then applies monitoring, testing, performance and recovery practices to the supplied shipment-processing example. The included demonstration uses a synthetic CSV of 20 shipments; it is a teaching prototype, not a production logistics system.

## P4 — Deployment approaches

**Manual deployment and execution** is started by an operator, for example by running `python pipeline.py`, clicking the dashboard’s “Run pipeline now” control, or selecting “Run workflow” in GitHub Actions. It is useful during development, for urgent reruns and for investigating a specific input. The operator can inspect logs and output immediately. However, manual runs depend on staff availability and consistent steps. Permissions, a documented checklist and a recorded run result reduce accidental execution against the wrong file or environment.

Run locally with `python pipeline.py` and `python app.py`; open `http://localhost:5000`.

**Scheduled deployment** separates the time a pipeline runs from a user request. A scheduler starts the same tested code at a defined interval, such as nightly. SkyRoute’s `.github/workflows/ci-and-schedule.yml` runs daily at 02:00 UTC, on pushes and pull requests to `main`, or on manual dispatch. The workflow installs dependencies, runs pytest, executes the pipeline and retains the processed CSV and JSON summary as an artifact. This produces repeatable reporting and an auditable run history. The schedule is not a guarantee of exact start time: platform queues and missed runs must be considered, and the team should monitor whether an expected artifact was produced. GitHub documents schedule triggers as workflow events, with the schedule defined in YAML (GitHub, n.d., accessed 2026).

**Serverless deployment** packages processing as a function or managed job invoked by a timer, file arrival or message (for example, an object-storage event). A provider manages servers and scales invocations, which suits irregular workloads and reduces idle infrastructure. It still requires explicit controls for execution limits, retries, duplicate events, concurrency and secret access. Long-running or high-volume transforms may need partitioning or a container job instead. A serverless function should be idempotent: retrying the same shipment batch must not duplicate financial or operational records.

The supplied `render.yaml` configures Render’s native Python web service, installs `requirements.txt`, runs the sample pipeline during build, starts Gunicorn bound to Render’s `$PORT`, and sets `/health` as the health check. Gunicorn serves the dashboard; `/api/summary` displays metrics and `/api/run` triggers processing. Render provides deployment history and runtime logs. Its HTTP health checks can prevent an unhealthy new instance receiving traffic (Render, n.d., accessed 2026). The generated files are local to the service and may not persist through a new deploy or restart, so production should store approved outputs in durable, access-controlled object storage or a database.

## P5 — Pipeline functions, reliability and security

A data pipeline moves data through defined stages: ingestion, validation, transformation, aggregation and delivery. Here, `pipeline.py` reads the supplied CSV, checks required fields, ISO dates, date order, known statuses, non-negative numeric cost and weight, and duplicate order/shipment identifiers. Invalid rows are counted with a row number and reason; valid rows receive a dispatch-to-delivery duration. It writes `output/processed_shipments.csv` and `output/pipeline_summary.json`. The lightweight dashboard shows pipeline progress, key row and cost metrics, a shipment-status bar chart, and a processed-versus-rejected chart. Detailed run messages are written to the Render/Gunicorn terminal logs. In the demonstrated run, all 20 rows were processed, none rejected, statuses were 14 Delivered, three In Transit and three Delayed, total shipping cost was 364.20, and mean weight was 5.08 kg.

Automation improves reliability when validation and tests run before release, and scheduling makes reporting consistent. Reconciliation checks should compare input rows with processed plus rejected rows and compare totals against expected business rules. For security, use least-privilege service identities, store credentials only in the platform’s secret manager, restrict production data access, encrypt data in transit and at rest, and avoid personal or shipment-sensitive values in logs. The supplied records are synthetic. Retain logs and output artifacts according to an approved policy, with access controls and integrity checks. NIST’s Secure Software Development Framework recommends embedding security practices across development rather than adding them only at release (NIST, 2022).

## P6 — Monitoring, diagnosis and tuning

Monitor each run’s start/end time, duration, input/processed/rejected counts, status distribution, output freshness and failure rate. The demo logs run completion and rejected row numbers; the dashboard probes `/health`; GitHub Actions stores test and execution results, and the hosting platform provides deployment/runtime logs. In production, route structured logs and metrics to a central service, alert on a failed job, missing expected output, unusual rejection rate or delayed schedule, and redact identifiers that could disclose sensitive data. Application logs should support operational and security review without collecting unnecessary information (OWASP, n.d., accessed 2026).

Troubleshooting begins by confirming the trigger and deployment version, checking input availability and schema, then inspecting the first failing log or test. Reproduce the issue with a small, representative CSV; check dates, nulls, duplicate keys, numeric parsing, permissions, quotas and output paths. Add a regression test for each confirmed defect. The included pytest tests cover a valid transformation, invalid cost rejection, duplicate shipment rejection, split shipments under one order, and malformed-date rejection. Unit tests isolate these rules; integration checks should additionally exercise the Flask endpoints and the scheduled workflow. A failed test should block release rather than be bypassed.

For slow runs, measure stage duration and profile before changing code. Reduce repeated parsing, process records in bounded batches, and use indexes or partitioning where the source permits. Independent CPU-heavy batches can be distributed with process-based parallelism; network-bound tasks may benefit from threads. Preserve deterministic output order, cap workers to available resources, and test that totals and rejection counts match the serial result. Python’s `concurrent.futures` supplies thread and process executors, but parallelism adds coordination overhead and should be benchmarked against the actual workload (Python Software Foundation, n.d., accessed 2026). Twenty sample rows do not justify adding it yet.

## M2 — Version control and rollback

Use Git as the source of truth: develop a change on a short-lived branch, submit a pull request, review the diff, and require passing unit tests and data checks before merging. Commit history identifies who changed validation or schedules and why; tags identify known-good releases. Pull requests support collaboration and catch defects before deployment. CI should test the exact revision that will be released, keep deployment credentials out of source, and grant the workflow only the permissions it needs. The included workflow provides test-on-push/PR and scheduled/manual execution, but this workspace has no recorded remote deployment history to claim as completed evidence.

Before each production release, record the deployed commit, retain the last known-good Render deploy and data artifact, and define an owner and recovery trigger. On failed health checks, incorrect totals or a spike in rejected rows, pause the next scheduled run, redeploy the prior known-good version, restore the previous output from versioned object storage, then rerun tests and reconcile row counts and business totals. Preserve failed logs for diagnosis, document the cause, and reprocess corrected inputs only after idempotency checks. Code rollback does not reverse data side effects: database migrations and external writes need a backward-compatible migration or a separately tested compensating/recovery procedure. This staged approach makes recovery quicker while retaining an audit trail.

## Supporting evidence

**Figure 1.** Deployment, monitoring, scheduled execution and rollback flow (diagram file: `LO3_Deployment_Monitoring_Rollback.png`; excluded from the word count).

**Evidence files:** `pipeline.py`; `tests/test_pipeline.py`; `docs/pipeline_test_run_output.txt`; `docs/pipeline_execution_log.txt`; `output/pipeline_summary.json`; `.github/workflows/ci-and-schedule.yml`; `render.yaml`; `app.py`; and the dashboard in `index.html`.

## References

- GitHub (n.d.). *Workflow syntax for GitHub Actions: schedule event*. Accessed 28 October 2026. https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- National Institute of Standards and Technology (NIST) (2022). *Secure Software Development Framework (SSDF) Version 1.1*, SP 800-218. https://csrc.nist.gov/pubs/sp/800/218/final
- OWASP (n.d.). *Logging Cheat Sheet*. Accessed 28 October 2026. https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- Python Software Foundation (n.d.). *concurrent.futures — Launching parallel tasks*. Accessed 28 October 2026. https://docs.python.org/3/library/concurrent.futures.html
- Render (n.d.). *Health checks*. Accessed 28 October 2026. https://render.com/docs/health-checks
