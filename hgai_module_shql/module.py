"""SHQL module descriptor for HypergraphAI."""


class SHQLModule:
    """SHQL (Semantic Hypergraph Query Language) module.

    Exposes a SPARQL-inspired pattern-matching query language for HypergraphAI
    via REST endpoints at /api/v1/shql/.
    """

    name = "shql"
    version = "0.1.0"
    description = (
        "SHQL (Semantic Hypergraph Query Language) — "
        "SPARQL-inspired variable binding and pattern matching for hypergraphs"
    )

    def get_router(self):
        from .api_router import router
        return router
