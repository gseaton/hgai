# Prompt

## Turn 1

Please update all documentation to reflect the current state of the project code base, features, and functionality (e.g. removal of HQL query language, improved documentation for SHQL query language, inferencing, etc).

## Turn 2 (clarification, via AskUserQuestion)

Question asked: "The 'removal of HQL' example implies documentation that HQL is gone — but HQL is still live in the code today. Should I actually execute the HQL code removal (the 'core removal' scope from the earlier plan: engine, API router, mesh/MCP/CLI branches, UI screen, tests) as part of this, so the docs are true, or keep the code as-is and document HQL as deprecated/being phased out rather than already gone?"

Answer selected: "Remove HQL from code + docs (Recommended)" — "Execute the core code removal now (module, API, mesh/MCP/CLI branches, UI screen, tests), then rewrite all documentation SHQL-only, with inferencing improved throughout. Matches the earlier sunset recommendation and makes 'removal' literally true."
