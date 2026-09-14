# Prompt

Please implement the following:

1. Port aggregate/group_by onto SHQL. This is the one thing standing between "SHQL is a superset" and "SHQL is a strict superset" — and it's a contained, additive change to     hgai_module_shql/engine.py's final items stage, mirroring the       
     existing HQL logic almost line-for-line.                                                                                                                                                                                                      
  2. Fix the drift you already have, independent of the sunset question: add "shql" to main.py's capabilities list, remove the already-shipped Roadmap bullet.                                                                                     
  3. Migrate the one UI dependency that's silently HQL-only — fetchInferredEdges in app.js — to SHQL syntax, so the viz doesn't privilege HQL by accident.
