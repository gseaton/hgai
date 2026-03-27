"""Mesh module descriptor for HypergraphAI."""


class MeshModule:
    """Mesh module.

    Provides mesh registry CRUD and active federation operations
    (health checks, graph sync, federated HQL queries) via REST
    endpoints at /api/v1/meshes/.
    """

    name = "mesh"
    version = "0.1.0"
    description = (
        "Mesh — distributed hgai server registry with federation, "
        "health checking, graph sync, and federated HQL queries"
    )

    def get_router(self):
        from .api_router import router
        return router
