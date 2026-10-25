# Feature Specification: Operations, Typed Actions Across Vendors

**Feature Branch**: `dga/feat-operation-s0e5v`

**Created**: 2026-10-25

**Status**: Draft

**Input**: Operations proposal
[nornir-automation/nornir#1089](https://github.com/nornir-automation/nornir/issues/1089),
with the feedback from dmzook (setting `changed` and `diff`) and theandrelima (NornFlow:
per-host parameters, runs on `SerialRunner`, registration conflicts and their sources,
listing contracts) in the issue's comments, refined in a grilling session on 2026-10-24. Add
an opt-in way to define an action once, with a typed input and a typed output, implement it
with ordinary Nornir tasks for each `(platform, connection)` pair, and run it across an
inventory with several vendors so that each host returns a typed result. Builds on the run
handle, the run stream and the runner capabilities of
[spec 003](../003-runner-streaming-cancellation/spec.md).

## User Scenarios & Testing *(mandatory)*

The primary user is the **caller**: a Python author who runs one logical action, such as
"get the running configuration", across an inventory with Cisco IOS, Arista EOS and Juniper
Junos hosts. Today they write `if host.platform == ...` branches, or import a different
vendor task per platform, and they receive an untyped `Result.result` whose shape they learn
by reading the task's source.

The second user is the **implementer**: the author of a package such as `nornir_napalm` or
`nornir_scrapli`, who publishes tasks that satisfy shared contracts. Story 1 cannot work
until an implementer has registered a task.

The third user is a **framework** built on Nornir, such as NornFlow. Its needs are in scope
only where they cost little and would be hard to add later: per-host parameters (Story 3),
the source of each registration and the list of contracts (Story 4).

The priorities show which story the others depend on. Stories 2, 3 and 4 each build on the
dispatch of Story 1, but are independent of each other.

### User Story 1 - Run one Operation across an inventory with several vendors (Priority: P1)

A caller defines, or imports, an Operation such as `GetConfig`, with an input model
`GetConfigInput` and an output model `GetConfigOutput`. They call
`nr.run_operation(GetConfig, connection="napalm", params=GetConfigInput())` and iterate over
`.results()`. For each host, Nornir selects the task registered for the host's platform and
the given connection, runs it, checks that the returned value is a `GetConfigOutput`, and
delivers one `Result[GetConfigOutput]`. The caller's code contains no condition on
`platform`, and their type checker knows that `res.result.config` is a `str`. This works on
every runner that supports streaming, including `SerialRunner`, which operators choose on
purpose during change windows.

**Why this priority**: This is the reason the feature exists. Without it, no other story
has anything to build on.

**Independent Test**: Register `get_config` for `ios.napalm` and `eos.napalm` with test
tasks, build an inventory with one IOS and one EOS host, run the Operation on
`SerialRunner` and on `ThreadedRunner`, and check that each host ran its own task and
returned a typed output. Type-check the calling code with the project's strict settings.

**Acceptance Scenarios**:

1. **Given** an inventory with IOS and EOS hosts, and `get_config` registered for
   `ios.napalm` and `eos.napalm`, **When** the caller iterates
   `nr.run_operation(GetConfig, connection="napalm", params=GetConfigInput()).results()` on
   `SerialRunner` or `ThreadedRunner`, **Then** each host yields exactly one
   `Result[GetConfigOutput]` produced by the task registered for its platform, and the type
   checker types `res.result.config` as `str`.
2. **Given** the same inventory and a connection default set in the Nornir configuration,
   **When** the caller runs the Operation without `connection=`, **Then** Nornir uses the
   configured connection for every host.
3. **Given** a host whose platform is `panos`, with nothing registered for
   `(get_config, panos, napalm)`, **When** the caller runs the Operation, **Then** that host
   fails with `OperationNotRegisteredError`, the message lists the implementations that are
   registered for `get_config`, and the other hosts complete normally.
4. **Given** an implementation that returns a `dict` instead of a `GetConfigOutput`,
   **When** the caller runs the Operation, **Then** that host fails with
   `OperationOutputError`, and the message names the task, the Operation, the returned type
   and the expected type.
5. **Given** an invalid static input such as `params={"sanitize": True}` (the field is
   `sanitized`), **When** the caller calls `run_operation`, **Then** it raises
   `OperationInputError` before any device is contacted, and no stream is returned.
6. **Given** a runner that supports background runs, **When** the caller starts the
   Operation with the background variant, **Then** they receive a `RunHandle[GetConfigOutput]`
   and the run proceeds while they do other work.

---

### User Story 2 - Report a change from an implementation (Priority: P2)

An implementer writes an Operation that changes the device, such as `ApplyConfig`. Their
task returns `Result(result=ApplyConfigOutput(...), changed=True, diff="...")` instead of a
bare output. The caller sees `changed` and `diff` on the host's `Result`, and tools that
already read these fields (`print_result`, NornFlow summaries and dry-run reports) keep
working.

**Why this priority**: Without it, Operations can only describe actions that read from the
device. dmzook and theandrelima both raised it.

**Independent Test**: Register an implementation that returns a `Result` with
`changed=True` and a diff, run the Operation, and check both fields and the type of
`result`.

**Acceptance Scenarios**:

1. **Given** an implementation that returns `Result(result=Out(...), changed=True,
   diff="...")`, **When** the caller runs the Operation, **Then** the host's `Result` has
   `changed=True`, the same diff, and a `result` that passed validation against the output
   model.
2. **Given** an implementation that returns `Result(failed=True, exception=err)` with no
   output, **When** the caller runs the Operation, **Then** the host fails with `err`, and
   Nornir does not check the output model.

---

### User Story 3 - Set different parameters for each host (Priority: P3)

A caller needs a value that differs per host, for example a backup path that contains the
host name, or an interface name read from the host's data. They pass
`params=lambda host: BackupInput(path=f"/backup/{host.name}")`. Nornir builds and validates
the input for each host when that host's task starts. A framework such as NornFlow, which
renders arguments per host from templates, uses the same mechanism.

**Why this priority**: Without it, a caller with per-host values must either run one
Operation call per host and lose concurrency, or fall back to plain tasks and lose the
contract.

**Independent Test**: Pass a callable that builds a different input per host, and check
that each host's task received its own input. Make the callable raise for one host and check
that only that host fails.

**Acceptance Scenarios**:

1. **Given** a `params` callable that returns a different input for each host, **When** the
   caller runs the Operation, **Then** each host's task receives the input built for that
   host.
2. **Given** a `params` callable that raises, or returns an invalid input, for host `r2`
   only, **When** the caller runs the Operation, **Then** `r2` fails with
   `OperationInputError`, and the other hosts complete normally.

---

### User Story 4 - List Operations and their implementations without running anything (Priority: P4)

A tool, such as NornFlow's `validate` and `show` commands or a catalogue of Operations,
lists every known Operation with its input model, its output model, its implementations,
whether each implementation is synchronous or asynchronous, and where each registration came
from. It does this without calling any task, including for an Operation that has no
implementation installed. When two installed packages register different tasks for the
same key, the user sees an error that names both packages.

**Why this priority**: Frameworks and catalogues need it, but callers of Story 1 do not.
Recording the source of each registration is in scope now because adding it later would
change what the registry stores.

**Independent Test**: Install a contract with no implementation, and a second contract with
two implementations from different sources. List the known Operations and check the
models, the implementations and their sources. Register a conflicting task and check the
error.

**Acceptance Scenarios**:

1. **Given** a contract package installed with no implementation, **When** a tool lists the
   known Operations, **Then** the contract appears with its input and output models and an
   empty list of implementations.
2. **Given** `get_config` implemented for `eos.napalm` by package `nornir_napalm`, **When** a
   tool reads the registration for that key, **Then** it gets the distribution and entry
   point, or the module and function, that registered it.
3. **Given** two installed packages that declare different tasks for
   `(get_config, ios, napalm)`, **When** Nornir loads the registrations, **Then** it raises
   `OperationAlreadyRegisteredError`, and the message names both sources.
4. **Given** a project that calls `register(..., replace=True)` for a key that a package
   already registered, **When** the caller runs the Operation, **Then** the project's task
   runs.

### Edge Cases

- **A host with no platform** (`platform=None`): the host fails with
  `OperationNotRegisteredError`, and the message says that the host has no platform rather
  than "nothing registered for platform None". The other hosts continue.
- **No connection given and none configured**: `run_operation` raises an error before any
  device is contacted, and no stream is returned.
- **A run that mixes synchronous and asynchronous implementations**: a host whose
  implementation does not match the runner fails with `AsyncTaskOnSyncRunError` or
  `SyncTaskOnAsyncRunError`. The other hosts continue. Nornir never adapts the
  implementation to the runner.
- **The same task registered twice under the same key**: accepted, so loading registrations
  repeatedly is safe.
- **An implementation registered for an Operation name with no known contract**: accepted
  when registered. The missing contract is reported when `run_operation` is called with that
  name, so the order in which packages load does not matter.
- **Two different Operation classes with the same name**: defining the second raises
  `OperationAlreadyRegisteredError`.
- **An implementation entry point with a malformed name** (for example `get_config.ios`, or
  a platform name that contains a dot): loading the package's registrations raises an error
  that names the distribution.
- **The Operation passed as a string** (`run_operation("get_config", ...)`): works for
  dynamic use, and the stream is typed with `Any`.
- **Cancellation, deadlines and progress**: an implementation is a task, so
  `PartialResult`, checkpoints, per-host and per-run deadlines and cancellation behave
  exactly as spec 003 defines for any task.
- **An input model without runtime type checks** (a standard `dataclass`): a wrong field
  type such as `retrieve=3` is not detected before the device is contacted. Only missing or
  unknown fields are. Authors who need type checks choose a model that validates them.

## Requirements *(mandatory)*

### Functional Requirements

**Running an Operation**

- **FR-001**: System MUST provide `run_operation`, which returns a typed `RunStream[Out]`
  that the caller consumes while the run progresses, on every runner that supports
  streaming, including `SerialRunner`. A runner that does not support streaming raises
  `RunnerCapabilityError`, as `run_stream` does.
- **FR-002**: System MUST provide a separate method, `submit_operation`, that returns a typed
  `RunHandle[Out]` on runners that support background runs, with the same capability rules
  as `submit`. Each method has a single return type.
- **FR-003**: System MUST provide asynchronous counterparts of FR-001 and FR-002 for the
  asyncio runner (`arun_operation` and `asubmit_operation`), following the rules of
  `astream` and `asubmit`.
- **FR-004**: System MUST select the task for each host from the Operation name,
  `host.platform` and the connection of the call.
- **FR-005**: `connection=` MUST be optional. When it is not given, System MUST use a single
  connection default set in the Nornir configuration, applied to every host. When neither is
  set, `run_operation` MUST raise an error before any device is contacted.
- **FR-006**: Users MUST be able to pass the Operation either as its class, which gives the
  type checker the output type, or as its name string, which gives a stream typed with
  `Any`.

**Input and output**

- **FR-007**: Users MUST be able to pass `params` as a static value (an instance of the input
  model, or a mapping of its fields). System MUST validate it once, before any device is
  contacted, and raise `OperationInputError` with no stream returned when it is invalid.
- **FR-008**: Users MUST be able to pass `params` as a callable that receives a `Host` and
  returns the input for that host. System MUST call it when that host's task starts. When
  the callable raises, or returns an invalid input, only that host MUST fail, with
  `OperationInputError`.
- **FR-009**: System MUST accept as an input or output model any class that can be built
  from keyword arguments, and MUST use the class's `model_validate` method when it provides
  one. System MUST NOT depend on any model library.
- **FR-010**: An implementation MUST be able to return either an instance of the output model
  or a `Result` that contains one. System MUST keep `changed`, `diff` and `severity_level` as
  the implementation set them.
- **FR-011**: System MUST check each host's output against the output model. A wrong type
  MUST fail that host with `OperationOutputError`. A `Result` returned with `failed=True` MUST
  NOT be checked against the output model, and its exception MUST be kept.

**Dispatch failures**

- **FR-012**: A host with no registered implementation for its key MUST fail with
  `OperationNotRegisteredError`, and the other hosts MUST continue. The message MUST list
  the implementations registered for the Operation. For a host whose platform is `None`, the
  message MUST say that the host has no platform.
- **FR-013**: System MUST NOT accept a registration for `platform=None`, and MUST NOT
  fall back to an implementation that applies to any platform.
- **FR-014**: System MUST check, for each host after selecting its implementation, whether
  the implementation is synchronous or asynchronous. A host whose implementation does not
  match the runner MUST fail with `AsyncTaskOnSyncRunError` or `SyncTaskOnAsyncRunError`,
  and the other hosts MUST continue.

**Registry**

- **FR-015**: Implementers MUST be able to register a task for an
  `(Operation name, platform, connection)` key both by a call in Python and by an entry point
  declared in their package, so that installing the package is enough. Entry points MUST use
  two fixed groups under the `nornir.plugins.*` namespace of constitution Principle II:
  - one group for contracts, where the entry-point name is the Operation name and the value
    is the Operation class;
  - one group for implementations, where the entry-point name is
    `<operation>.<platform>.<connection>` and the value is the task.
- **FR-015a**: An implementation entry-point name that does not have exactly three parts
  separated by dots MUST raise an error when the package's registrations are loaded, and the
  error MUST name the distribution. As a result, Operation, platform and connection names
  used in entry points cannot contain dots.
- **FR-016**: When a different task is registered for a key that is already taken, System
  MUST raise `OperationAlreadyRegisteredError`, unless the registration explicitly asks to
  replace the existing one. Registrations declared through entry points MUST NOT be able to
  replace. Registering the same task twice under the same key MUST be accepted.
- **FR-017**: System MUST record the source of each registration (the distribution and entry
  point, or the module and function of the task) and let callers read it. The conflict
  error of FR-016 MUST name both sources.
- **FR-018**: Each Operation class MUST be registered under its unique name when it is
  defined. Defining a second, different class with the same name MUST raise
  `OperationAlreadyRegisteredError`.
- **FR-019**: System MUST list the known Operations with their input model, output model,
  implementations, the kind of each implementation (synchronous or asynchronous) and the
  source of each, without calling any implementation task. Listing may import the modules
  that define the tasks, because reporting the kind of a task requires the task itself. An
  Operation is known once its module is imported or once a package declares it.
- **FR-020**: System MUST accept an implementation registered for a name with no known
  contract, and MUST report the missing contract when `run_operation` is called with that
  name.

**Compatibility and debuggability**

- **FR-021**: Code that uses a bare `Result`, `RunStream` or `RunHandle` annotation MUST keep
  passing a type checker with the project's strict settings (`disallow_any_generics`), and
  the core MUST NOT take a new runtime dependency to achieve this. If making the existing
  `Result` generic cannot meet this, Operations MUST return a new typed result class and the
  existing `Result` MUST stay unchanged.
- **FR-022**: When a caller steps through a run with `pdb`, or reads a traceback, the
  selected implementation task MUST appear as a direct frame, with no more dispatch frames
  than a plain `nr.run` adds.
- **FR-023**: `nr.run`, `run_stream`, `submit` and the plain-task contract MUST behave
  exactly as before. An implementation MUST remain a plain task that can also be run
  directly with `nr.run(task=..., params=...)`.
- **FR-024**: Operations MUST go through the same runner, processors, dry-run setting,
  cancellation, deadlines and progress events as any task under spec 003.

### Key Entities

- **Operation** (new): a named contract with an input model and an output model. It contains
  no vendor logic. It is registered under its unique name when it is defined.
- **Input model / output model** (new concept, author-chosen classes): the classes that
  describe what an Operation needs and what it returns. A `dataclass` or a Pydantic model
  both work; the Operation's author chooses per Operation.
- **Implementation** (existing concept, a plain task): a task registered for one
  `(Operation name, platform, connection)` key, together with the source of the
  registration. It receives the validated input as `params`.
- **Operation registry** (new): stores the Operations and their implementations, detects
  conflicts, records sources, and lists what is known.
- **Run stream / run handle / result** (existing, from spec 003): made generic over the
  output model, or, under FR-021's fallback, a new typed result class used only by
  Operations.
- **Host platform** (existing): part of the dispatch key, used as written in the inventory.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A caller runs one Operation across an inventory with at least three platforms,
  and the caller's code contains zero conditions on the host's platform. A how-to notebook
  executed in CI demonstrates this.
- **SC-002**: In that notebook and in the tests, the type checker types each host's result as
  the Operation's output model, with zero casts and zero type-check suppressions.
- **SC-003**: Each of the seven failure cases (invalid input, no implementation registered,
  host with no platform, output of the wrong type, synchronous or asynchronous mismatch, no
  connection given or configured, conflicting registrations) produces an error that names
  the Operation, names the host where one applies, and states the information needed to fix
  it. One test covers each case.
- **SC-004**: Code that does not use Operations behaves exactly as before: the existing test
  suite passes unchanged, and the core takes zero new runtime dependencies.
- **SC-005**: Before the release, at least one package outside the Nornir repository (for
  example a prototype branch of `nornir_napalm`, or NornFlow) registers implementations
  through entry points and is run end to end against the release candidate.

## Decisions on the Issue's Open Questions

- **Blocking by default**: `run_operation` returns a stream that the caller consumes
  attached to the call, and a separate method, `submit_operation`, runs in the background
  (FR-001, FR-002). This replaces the issue's design of one method that always returns a
  background handle, which would have raised on `SerialRunner`. A `background=True`
  argument was rejected because the return type would depend on an argument.
- **Naming**: the concept keeps the name **Operation**. "Action" was the alternative.
- **Entry-point layout**: two fixed groups under `nornir.plugins.*`, one for contracts and
  one for implementations with structured names (FR-015). One group per Operation, as in the
  issue, was rejected because `importlib.metadata` cannot list groups by prefix, so Nornir
  could not list Operations it does not already know (FR-019).

## Clarifications

### Session 2026-10-25

- Q: What is the name and form of the background variant? → A: A separate
  `submit_operation` method, and `asubmit_operation` on the asyncio runner (FR-002, FR-003).
- Q: How are contracts and implementations declared as entry points? → A: Two fixed groups
  under `nornir.plugins.*`; implementation names are `<operation>.<platform>.<connection>`,
  and a name without exactly three parts is an error (FR-015, FR-015a).

## Assumptions

- Spec 003 (#1086) is merged and released before this feature. The run handle, the run
  stream and the runner capability rules are reused as they are.
- Implementers use the platform strings that inventories already use (`ios`, `eos`,
  `junos`, …). Nornir does not normalise platform names.
- A default type parameter on `Result`, declared so that only the type checker reads it,
  meets FR-021 without a runtime dependency. The plan checked this with mypy and on Python
  3.10, 3.12 and 3.14 ([research R1](research.md)), so the fallback is not used.
- Operations are additive: they ship in a MINOR release with no upgrade guide. A new module
  under `nornir/core/` requires regenerating and committing `docs/api/nornir/**`.
- The plugin contracts (`ConnectionPlugin`, `InventoryPlugin`, `RunnerPlugin`, `Processor`,
  `TransformFunction`) do not change.

### Out of Scope

- A catalog of standard Operations (`get_config`, `get_facts`, …) shipped with the core. The
  catalog is a community effort in companion packages.
- Dispatch by OS version or device model.
- An implementation that applies to any platform, such as a pure-NETCONF `get_config`.
- A per-host default connection stored in the inventory. The single default in the Nornir
  configuration is in scope.
- A check before the run that every host has an implementation.
- Nornir adapting a synchronous implementation to an asynchronous runner, or the reverse.
- A command-line tool to list Operations. The Python API to list them (FR-019) is in scope.
- NornFlow integration itself. Nornir provides what NornFlow needs: per-host `params`, the
  source of each registration and the list of contracts.
