# Capability-aware connection plugin direction

## Agreed terminology

The successor connection plugin contract uses the capability-aware naming family:

- Protocol: `CapabilityConnectionPlugin`
- Registry: `CapabilityConnectionPluginRegister`

The new registry accepts plugins implementing the new contract, whether they support
synchronous execution, asyncio execution, or both. It is not an async-only registry.
The contract must provide a method reporting the plugin's supported execution capabilities.

`ConnectionPlugin` and `ConnectionPluginRegister` remain the legacy compatibility contract
and registry. Existing plugins are not required to implement the new capability method.

## Design work required

This direction supersedes the async-only registry proposal. It is incorporated into
`spec.md`, including FR-011–FR-013, FR-021–FR-023, SC-005, and SC-007. The revised
`plan.md`, `research.md`, `data-model.md`, `contracts/`, and `quickstart.md` now define
the design. `tasks.md` has been regenerated against these artifacts with requirement
coverage and an old-to-new task ID mapping. Cross-artifact analysis precedes implementation.

Planning selects an instance `get_capabilities()` method returning a nonempty
`frozenset[Literal["sync", "asyncio"]]`, separate typed operation facets, and discovery
through `nornir.plugins.capability_connections`. Sync-capable instances retain the public
connection cache; async-only instances have a private typed cache, with identity-matched
origin metadata. Cross-registry duplicate names are rejected on get/open. Full signatures
and lifecycle behavior are in `contracts/`; these are planning decisions implementing
the agreed naming and scope above.
