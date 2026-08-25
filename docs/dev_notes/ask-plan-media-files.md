❯ Make no code changes but please assess how to store media / binary files efficiently and reference those media files with attributes as associated media (e.g. 'media' list of dicts/maps with the media identifier and attributes of how the     
  media relates to the hypernode/hyperedge).                                                                                                                                                                                                        
  
● fork(Research current storage architecture for media assessment)
  ⎿  Backgrounded agent (↓ to manage · ctrl+o to expand)

● I've dispatched a fork to gather the concrete facts about the current data models, storage backend, dependencies, and deployment setup — I'll use those to ground a real design recommendation rather than generic advice. I'll report back once
  it's done.

✻ Waiting for 1 background agent to finish

● Agent "Research current storage architecture for media assessment" finished · 41s

● Assessment: Storing & Referencing Media in HypergraphAI

  No code changes made — this is a design assessment only, grounded in the actual codebase (storage abstraction, existing model patterns, dependencies, and deployment).

  Current state (why this needs new infrastructure)

  - No media/binary concept exists today. The storage layer (hgai_module_storage/backend.py) is a clean pluggable ABC + registry (registry.py), but every store method (hgai_module_storage_mongodb/stores/*.py) deals only in JSON-serializable
    dicts. No GridFS, no blob store, no file concept anywhere.                                                                                                                                                                          
  - Only MongoDB is registered as a backend (storage_backend config defaults to "mongodb", no S3/blob settings in hgai/config.py).
  - docker-compose.yml provisions only mongo + the app — no object-storage service, no persistent volume for local files (the container mount is ./scripts:/app/scripts:ro, read-only).
  - python-multipart is already a dependency (unused today, only pulled in transitively for OAuth2 form login) — this is exactly what FastAPI needs for UploadFile, so file-upload endpoints are "one router away," not a new dependency.
  - There's already a precedent for exactly the shape you described: Hyperedge.members: List[EdgeMember], where EdgeMember is its own small typed model (node_id, seq). A media: List[MediaRef] field should follow that same pattern, not the
    untyped attributes: Dict[str, Any] bag every entity already has.

  The key efficiency decision: don't store bytes in the graph documents

  MongoDB caps a document at 16MB, and even well under that, embedding binary data in a hypernode/hyperedge document bloats every graph read, backup, and replication cycle — including ones that never touch the media. The efficient pattern is a
  level of indirection: hypernode/hyperedge documents carry only a small reference; the actual bytes live in a separate, purpose-built store.

  Concretely, that means two new pieces:

  1. A media first-class entity (its own collection, like hypernodes/hyperedges get today) holding metadata: id, content_type, filename, size_bytes, checksum (sha256 — enables dedup and integrity checking), uploaded_by, uploaded_at, and a
  ref_count for garbage collection. The bytes themselves live behind a pluggable MediaStore abstraction (mirroring the existing StorageBackend registry pattern) — Phase 1 implementation: MongoDB GridFS, since it needs zero new infrastructure
  and works with the existing docker-compose.yml as-is (motor already supports it via AsyncIOMotorGridFSBucket). Phase 2, opt-in: an S3-compatible store (MinIO self-hosted or real S3) for when files get large or numerous enough that keeping
  them in the primary MongoDB instance becomes a backup/scaling concern.

  2. The reference field itself, exactly as you sketched — added to the shared base model so every entity type gets it for free:

  class MediaRef(BaseModel):                                                                                                                                                                                                            
      media_id: str                          # points at the media entity above, not raw bytes
      role: Optional[str] = None             # "profile-photo", "attachment", "source-document", ...
      content_type: Optional[str] = None     # cached, avoids a round-trip for display
      filename: Optional[str] = None
      attributes: Dict[str, Any] = Field(default_factory=dict)  # free-form, same convention as elsewhere

  # in HgaiBaseModel (common.py), alongside tags/status/attributes:
  media: List[MediaRef] = Field(default_factory=list)
  
  Because media_id is an opaque reference (not a URL or path), the same uploaded file can be attached to many hypernodes/hyperedges without duplicating storage, and swapping GridFS→S3 later requires no data-model migration.         

  API surface would be a small new router: POST /media (multipart upload → returns media_id), GET /media/{id} (streamed download), DELETE /media/{id} (refcount-gated). Existing hypernode/hyperedge create/update calls just attach an
  already-uploaded media_id — no change to how graph writes work today.

  One architecture-specific wrinkle worth flagging

  already-uploaded media_id — no change to how graph writes work today.

  One architecture-specific wrinkle worth flagging

  HGAI already supports a mesh of federated servers (capabilities: [..., "mesh"]). If each mesh server has its own MongoDB, a media_id created on server A won't resolve on server B unless media is either (a) proxied through the mesh query layer
  on read, or (b) backed by a network-shared store (S3/MinIO reachable by every mesh member) rather than per-server GridFS. This only matters if media needs to be visible across mesh-federated queries — worth deciding before committing to
  GridFS-only, since it affects which "Phase 1" default makes sense for your actual deployment topology.

  Want me to turn this into an implementation plan (models, migration, endpoints, and which media store to start with) once you're ready to build it?

✻ Sautéed for 2m 9s

❯ Yes, turn this into an implementation plan but allow for media reference identifiers to include mesh servers (e.g. <mesh-hgai-server>/<media-identifier> for remote media references, <media-identifier> for local media references).             

● Implementation Plan: Media Storage & Mesh-Qualified References

  Still no code changes — this turn produces the plan; nothing is written to the repo yet.

  Identifier scheme

  <media-identifier>                    — local media, owned by the server currently being queried
  <mesh-hgai-server>/<media-identifier> — remote media, owned by another server in the mesh

  - media-identifier is a UUID4/ULID (or content-hash) by construction — never contains a / — which makes parsing unambiguous: split on the first /; if there's none, it's local.
  - mesh-hgai-server is the same server_id already used to identify a MeshServer entry within a Mesh (the id shown in the existing Meshes admin screen).
  - Media is always stored unqualified in the database — a hypernode's media list on disk never contains a /, even if that hypernode is currently being served across the mesh. Qualification happens only at the response boundary (see Phase 3),
    the same way _mesh_server_id is already injected into federated HQL/SHQL results without being persisted in the underlying documents. This means a server's own server_id can change without ever needing a data migration.

  Phase 1 — Foundations (local-only, no mesh yet)

  - Models (new hgai/models/media.py): Media/MediaCreate/MediaResponse (id, content_type, filename, size_bytes, checksum, uploaded_by, uploaded_at, ref_count) plus:
  class MediaRef(BaseModel):                                                                                                                                                                                                            
      media_id: str                       # "<id>" or "<server>/<id>"
      role: Optional[str] = None          # "profile-photo", "attachment", ...
      content_type: Optional[str] = None  # cached for display without a round-trip
      filename: Optional[str] = None
      attributes: Dict[str, Any] = Field(default_factory=dict)
    Add media: List[MediaRef] = Field(default_factory=list) to HgaiBaseModel (common.py) — every entity type (hypernode, hyperedge, hypergraph, space, account) gets it for free, same as tags/attributes today.
  - Storage: new MediaStore ABC in hgai_module_storage/backend.py (put, get_stream, delete, get_metadata) alongside the existing store ABCs; a GridFS implementation in hgai_module_storage_mongodb/stores/media.py via AsyncIOMotorGridFSBucket —
    zero new infrastructure, works with today's docker-compose.yml unchanged.
  - API (hgai/api/routers/media.py): POST /media (UploadFile — python-multipart is already a dependency), GET /media/{media_id} (local ids only in this phase), DELETE /media/{media_id} (refcount-gated).
  - Refcounting: increment/decrement on attach/detach happens in hgai/core/engine.py, not inside the Mongo store — keeps the storage backend swappable and matches how the engine already orchestrates rather than the store layer.

  Phase 2 — UI

  - ui/js/api.js: uploadMedia, mediaUrl(id), deleteMedia.
  - Node/edge modals: a file-attach control that uploads immediately on selection and pushes the resulting media_id into the entity's media list (mirroring how attributes is already edited as structured data in those modals).

  Phase 3 — Mesh-qualified addressing

  - Shared helper (e.g. hgai/core/media.py): parse_media_id(id) -> (server_id | None, local_id).
  - GET /media/{media_id}: if qualified, resolve server_id → that MeshServer's base URL (same lookup queryMesh/pingMesh already use), then proxy-fetch {remote_url}/api/v1/media/{local_id} and stream the response back — reusing whatever HTTP
    client/auth hgai_module_mesh/engine.py already uses for federated HQL calls. Proxy-by-default (not a redirect) for consistency with how federated queries already work server-side rather than pushing mesh topology knowledge onto the
    browser/MCP client; a redirect mode can be added later as an optimization.
  - Wherever hgai_module_hql/hgai_module_shql already annotate federated results with _mesh_server_id, add the matching step: rewrite any bare media_id in a returned media list to "<this_server_id>/<media_id>" before the result crosses back
    over the mesh boundary. Purely local (non-federated) reads never rewrite — satisfies "<media-identifier> for local" directly.

  Phase 4 — Hardening (not blocking, do after the above works)

  - Optional S3-compatible MediaStore behind the same ABC, config-toggled — no model changes needed, media_id stays opaque either way.
  - Checksum-based dedup, orphan-reconciliation sweep as a GC safety net (belt-and-suspenders alongside refcounting), MCP tool exposure for agent-driven upload/download, tests.

  Open question before I start building

  Server-to-server auth for the Phase 3 proxy fetch needs to reuse whatever mechanism mesh servers already authenticate each other with today — I didn't verify that mechanism in the last research pass. Want me to check that first, or start on
  Phase 1 (which doesn't need it) while that's pending?

✻ Crunched for 1m 36s

❯ Check the mechanism for mesh server authentication before planning for Phase 1.                                                                                                                                                                   

● fork(Research mesh server-to-server auth mechanism)
  ⎿  Backgrounded agent (↓ to manage · ctrl+o to expand)

● I've dispatched a fork to trace the exact mesh server-to-server authentication mechanism (models, the actual HTTP call code, and how incoming API keys get validated) — I'll report back with a concrete answer once it's done.

 Agent "Research mesh server-to-server auth mechanism" finished · 53s

● Mesh Server-to-Server Auth: Confirmed

  The mechanism already exists and answers the Phase 3 open question directly — no new auth code needed for the media proxy.

  How it works today:
  - MeshServer (hgai_module_mesh/models.py:10-25) already has an optional api_token field, settable per-server in the existing mesh-server-add UI form.
  - Every outbound mesh call (hgai_module_mesh/engine.py:80-84) attaches Authorization: Bearer <server.api_token> via a shared httpx.AsyncClient. 
  - On the receiving end, that bearer token is checked in hgai/core/auth.py:38-44 against HGAI_PRIMARY_API_KEY/HGAI_SECONDARY_API_KEY (env-configured) — a match resolves to a synthetic full-admin account, no JWT/username involved.  
  
  For Phase 3, the media proxy just reuses this verbatim: build the GET /media/{local_id} request to the remote server with the same Authorization: Bearer <server.api_token> header (calling the same _headers() helper or replicating its one
  line), send it through the same shared HTTP client. The receiving server authenticates it through its existing, unmodified get_current_account dependency — zero new auth code on either side.

  One caveat worth flagging: this is a flat shared secret, not a scoped/per-server credential. Whoever holds a remote server's api_token gets full admin-equivalent access to that remote — not scoped to media. The media-proxy feature inherits
  that same blast radius rather than introducing a new one; it's not a regression, but it does mean a compromised mesh media reference is equivalent to a compromised admin API key on that remote, not a narrower "read-only media" exposure. Worth
  knowing before relying on cross-mesh media in anything sensitive.

  With that resolved, Phase 1 (local-only models/storage/API, no mesh dependency at all) is unblocked and doesn't touch this auth path. Want me to start implementing Phase 1 now, or do you want to review/adjust the full plan first?
  
 Here is Claude's plan:
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
 Media Storage & Mesh-Qualified References — Implementation Plan
  
 Context                                                                                                                                                                                                                                

 HypergraphAI currently has no way to attach binary files (images, PDFs, documents, etc.) to hypernodes or hyperedges — the only extensibility mechanism is the untyped attributes: Dict[str, Any] bag, which is unsuitable for binary content
 (MongoDB's 16MB document cap, no streaming, no dedup, no garbage collection). The user wants an efficient, mesh-aware way to store media and reference it from entities as a media: List[MediaRef] field — each ref carrying an identifier plus
 attributes describing how the media relates to that entity (matching the existing Hyperedge.members: List[EdgeMember] pattern).

 Because HGAI already supports a federated mesh of servers, a hypernode/hyperedge synced or queried across the mesh may need to reference media that physically lives on a different server. The identifier scheme must distinguish local from
 remote media:

 <media-identifier>                    — local media, owned by the server currently being queried
 <mesh-hgai-server>/<media-identifier> — remote media, owned by another server in the mesh

 media-identifier is a UUID4/ULID by construction (never contains /), so parsing is unambiguous: split on the first /; no / means local. Media is always stored unqualified in the database — qualification only happens at the response boundary
 when data crosses a mesh server, the same way _mesh_server_id is already annotated into federated HQL/SHQL results without being persisted.

 This session's research (two deep-dive investigations) confirmed the concrete integration points below; nothing here is speculative.

 Approach

 Data model

 New hgai/models/media.py:
 class Media(TimestampedModel):          # metadata record, its own Mongo collection
     id: str
     content_type: str
     filename: Optional[str] = None
     size_bytes: int
     checksum: str                        # sha256, for integrity + future dedup
     uploaded_by: str
     ref_count: int = 0

 class MediaRef(BaseModel):               # embedded in hypernode/hyperedge/etc. `media` lists
     media_id: str                        # "<id>" or "<server>/<id>"
     role: Optional[str] = None           # "profile-photo", "attachment", "source-document", ...
     content_type: Optional[str] = None   # cached, avoids a round-trip for display
     filename: Optional[str] = None
     attributes: Dict[str, Any] = Field(default_factory=dict)
 Add media: List[MediaRef] = Field(default_factory=list) to HgaiBaseModel in hgai/models/common.py (alongside the existing tags/status/attributes fields) — every entity type (hypernode, hyperedge, hypergraph, space, account) gets it for free,
 consistent with how those other shared fields already work.

 Why indirection, not embedding bytes: raw bytes never live in a hypernode/hyperedge document. Media is its own entity (like a hypernode is), the bytes live in GridFS, and MediaRef.media_id just points at it — the same file can be referenced
 by many entities without duplicating storage, and swapping the storage backend later needs no data migration since media_id stays opaque.

 Storage backend

 New MediaStore ABC in hgai_module_storage/backend.py, alongside the existing HypergraphStore/HypernodeStore/HyperedgeStore ABCs and registered the same way (registry.py): put(id, stream, content_type) -> Media, get_stream(id), delete(id),
 get_metadata(id).

 Mongo implementation: hgai_module_storage_mongodb/stores/media.py, following the exact shape of the existing stores/hypernodes.py/stores/hyperedges.py. Bytes go through motor's AsyncIOMotorGridFSBucket (motor is already a dependency, already
 used for the async Mongo client in connection.py) via open_upload_stream_with_id(media_id, ...) / open_download_stream(media_id) — stream, never await file.read() the whole thing, to avoid buffering large files in memory. Metadata (the Media
 record above) goes in its own media collection, keyed by the same id used for the GridFS file, so no separate id-mapping field is needed. This requires zero new infrastructure — GridFS lives inside the same MongoDB the graph data already
 uses, and docker-compose.yml needs no changes.

 API

 New hgai/api/routers/media.py, following the pattern of hgai/api/routers/hypernodes.py:
 - POST /media — UploadFile (multipart; python-multipart is already a dependency, confirmed unused-but-present today) → creates the Media record + GridFS blob, returns {media_id, content_type, filename, size_bytes, checksum}.
 - GET /media/{media_id} — local ids only in Phase 1 (see Phase 3 for mesh-qualified resolution); streams the GridFS content back via StreamingResponse.
 - DELETE /media/{media_id} — refcount-gated; refuses (409) if ref_count > 0.

 Config: add max_media_size_mb to hgai/config.py (no size cap exists today) and reject oversized uploads before streaming completes.

 Refcounting (attach/detach)

 Lives in hgai/core/engine.py (the existing orchestration layer — this is exactly where export_hypergraph/import_hypergraph_data already live, at lines 360/377, rather than inside the Mongo store, keeping the storage backend swappable), not
 inside the Mongo store:
 - On hypernode/hyperedge create or update: diff the incoming media list against the existing one, increment ref_count for newly-added local media_ids (parse first — skip anything containing /, since remote-qualified media is refcounted by its
   origin server, not this one), decrement for removed ones.
 - On hypernode/hyperedge delete: decrement ref_count for all of its local media refs.

 Mesh-qualified addressing (Phase 3)

 This session confirmed the exact mechanism to reuse — no new auth code needed:
 - MeshServer (hgai_module_mesh/models.py:10-25) already has an api_token field, settable per-server in the existing mesh-server-add UI.
 - Every outbound mesh call already attaches Authorization: Bearer <server.api_token> via _headers() (hgai_module_mesh/engine.py:80-84) and a shared pooled httpx.AsyncClient.
 - Inbound, that bearer token is validated in hgai/core/auth.py:38-44 against HGAI_PRIMARY_API_KEY/HGAI_SECONDARY_API_KEY — a match resolves to a full-admin synthetic account via the existing get_current_account dependency.

 So: a shared parse_media_id(id) -> (server_id | None, local_id) helper (new small module, hgai/core/media.py), and GET /media/{media_id} gains a branch: if qualified, resolve server_id → that MeshServer's url, build the same _headers(server)
 bearer-token header, and proxy-fetch (not redirect) {remote_url}/api/v1/media/{local_id}, streaming the response straight back — mirroring how federated HQL queries already resolve server-side rather than pushing mesh topology onto the
 caller.

 Self-qualification on the way out: wherever the HQL/SHQL engines (hgai_module_hql/engine.py, hgai_module_shql/engine.py) currently annotate federated results with _mesh_server_id, add the equivalent rewrite of any bare media_id in a returned
 media list to "<this_server_id>/<media_id>" before the result crosses the mesh boundary. The exact injection point needs to be located during implementation (not pinned down by this session's research) but the pattern to follow — find where
 _mesh_server_id is already added and mirror it — is confirmed to exist.

 Known trade-off to flag, not solve here: mesh auth today is a flat shared secret (any holder of a remote's API key gets full admin access there, not scoped to media) — the media-proxy feature inherits that blast radius rather than introducing
 a new one.

 UI (Phase 2)

 ui/js/api.js: uploadMedia, mediaUrl(id), deleteMedia, following the existing method style (e.g. createGraph/getGraph). Node/edge modals (openNodeModal/openEdgeModal in ui/js/app.js) get a file-attach control that uploads on selection and adds
 the resulting media_id to the entity's media list.

 Later hardening (Phase 4, not blocking)

 Optional S3-compatible MediaStore behind the same ABC (config-toggled, no model changes needed), checksum-based dedup, an orphan-reconciliation sweep as a GC safety net alongside refcounting, MCP tool exposure for agent-driven
 upload/download, redirect-mode as a proxy-bandwidth optimization.

 Files to touch (Phase 1, the actionable next step)

 - hgai/models/media.py — new: Media, MediaCreate, MediaResponse, MediaRef
 - hgai/models/common.py — add media: List[MediaRef] to HgaiBaseModel
 - hgai_module_storage/backend.py — new MediaStore ABC
 - hgai_module_storage/registry.py — register it alongside existing store types
 - hgai_module_storage_mongodb/stores/media.py — new, GridFS-backed implementation
 - hgai_module_storage_mongodb/backend.py — wire the new store in, same as existing ones
 - hgai/api/routers/media.py — new router (POST/GET/DELETE /media)
 - hgai/api/deps.py / wherever routers are mounted (hgai/main.py) — register the new router, same pattern as the existing ones
 - hgai/core/engine.py — refcount hooks in the existing hypernode/hyperedge create/update/delete orchestration methods
 - hgai/config.py — max_media_size_mb
 - tests/test_media.py — new, following tests/test_engine.py's style

 Verification

 1. Automated: tests/test_media.py — upload round-trips bytes correctly (content matches, checksum matches), attaching a media_id to a hypernode via the existing node-create/update path increments ref_count, detaching/deleting the hypernode
    decrements it, DELETE /media/{id} is refused while ref_count > 0 and succeeds once it's 0. Run via the existing run_all_tests skill/pytest.
 2. Manual smoke test: same local-dev pattern already used this session (spin up mongod + python -m hgai.main against a scratch DB) — curl -F file=@sample.png localhost:8357/api/v1/media → capture media_id → curl -X PATCH .../nodes/{id} with
    that media_id in its media list → curl localhost:8357/api/v1/media/{media_id} and diff the bytes against the original file.
 3. Mesh proxy (Phase 3 only): two local hgai instances against separate Mongo DBs, mesh-linked with a shared api_token; upload media on server A, attach it to a hypernode's media list with a B/<id>-style ref stored on server B (or verify a
    federated HQL query naturally produces the qualified id), then confirm GET /media/B/<id> on server A proxies through and returns the correct bytes.
╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
