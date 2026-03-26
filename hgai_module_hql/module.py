"""HQL module descriptor for HypergraphAI."""


class HQLModule:
    """HQL (Hypergraph Query Language) module.

    Exposes a YAML-based declarative query language for HypergraphAI
    via REST endpoints at /api/v1/query/.
    """

    name = "hql"
    version = "0.1.0"
    description = (
        "HQL (Hypergraph Query Language) — "
        "YAML-based declarative query language for hypergraphs"
    )

    def get_router(self):
        from .api_router import router
        return router
