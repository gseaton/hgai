# Prompt

Please generate a markdown plan 'docs/architect/telemetry-<yyyymmddhhmmss>.md' to implement OTEL telemetry on usage and errors for further analysis for hot spots, most-used features, least-used features, by account, error / bug reporting.  Please allow for a configurable endpoint to post each OTEL JSON message (e.g. https://telemetry.hypergra.ai/report).

---

**Turn 2**

Please amend plan to store telemetry in its own hypergraph `__local-telemetry` with each OTEL log message JSON as the attributes, Type of OTEL, Name of `<generated-3-4-word-slug>-<yyyymmddhhmmss>', Description is the OTEL JSON message, if no external endpoint is defined or local telemetry option is enabled.
