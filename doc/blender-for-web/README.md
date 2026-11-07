# Blender for Web — Project Engineering Index

> Status: Phase 1.1 architecture mapping merged. Phase 1.2 static research deliverables prepared on `dev/p1-dependencies`; source/link configuration validation remains in Phase 1.3.
>
> Source baseline: Blender **5.4 Alpha** (`BLENDER_VERSION 504`, cycle `alpha`), commit `67e5a5f874cf37e2a114cebd24f219d8c44a16ad`.
>
> This project deliberately retains the current alpha fork. It does **not** switch to an LTS release.

## Repository policy

- `main`: upstream Blender fork. Do not put web-port modifications here.
- `blender-for-web`: integration branch for this project.
- `dev/p1-architecture`, `dev/p1-dependencies`, and subsequent `dev/p*-*` branches: working branches, created from the latest `blender-for-web`.
- Pin the source baseline for reproducibility; do not automatically sync upstream while removing dependencies.
- Keep a record of any later cherry-picked upstream fixes, including source SHA, rationale and affected subsystem.
- Preserve copyright notices and account for Blender's GPL obligations when distributing the port.

## Three phases, three subphases each

| Stage | Goal | Exit gate |
| --- | --- | --- |
| 1.1 — Architecture & feature mapping | Understand code ownership, execution flow, modeling feature boundaries and target scope | Documented architecture, traceable flows, initial feature contract |
| 1.2 — Dependency analysis | Trace CMake, generated-source, include, symbol and external dependency closure | Auditable dependency graph and candidate extraction boundary |
| 1.3 — Feasibility | Validate native build and early Emscripten proof of concept | Reproducible native baseline and small Blender-derived WASM operation |
| 2.1 — Component classification | Keep / isolate / replace / exclude decisions | Approved component matrix |
| 2.2 — Core extraction | Reduce build graph without premature deletion | Buildable reduced native modeling core |
| 2.3 — Stabilization | Preserve results and memory safety | Regression-tested native core |
| 3.1 — WebAssembly integration | Browser-accessible engine APIs | Running WASM core with reliable JS bindings |
| 3.2 — Viewport & interaction | Browser graphics, selection and tools | Interactive 3D editing viewport |
| 3.3 — Product integration | UI, persistence, import/export, optimization | Deployable tested web modeling application |

## Phase 1 records

- [1.1 — Architecture and feature mapping](phase-1/1.1-architecture.md)
- [1.2 — Dependency audit ledger](phase-1/1.2-dependencies.md)
- [1.2 — CMake target graph and SCCs](phase-1/1.2-target-graph.md)
- [1.2 — Cuboid/BMesh source paths](phase-1/1.2-source-closure.md)
- [1.2 — Native closure verification handoff](phase-1/1.2-validation-handoff.md)
- [1.2 — Executed CI verification and remaining linker blocker](phase-1/1.2-ci-verification.md)

## Evidence and limitations

Documented conclusions must distinguish **CMake target links**, **source include/symbol dependencies** and **actual runtime needs**. A target-level edge does not prove that a feature uses a dependency at runtime. Phase 1.1 documents verified representative source paths; it is **not** a file-by-file or link-tested dependency closure. No native or WebAssembly compilation is claimed at this stage.

### Architecture decision log

| ID | Decision | Status |
| --- | --- | --- |
| ADR-001 | Keep Blender 5.4 Alpha as source baseline, SHA above | Confirmed |
| ADR-002 | Protect `main`, integrate through `blender-for-web` | Confirmed |
| ADR-003 | Target a web editor centered on modeling, texturing and editing; defer advanced rendering/simulation/animation workflows | Working product boundary; refine in 2.1 |
| ADR-004 | Investigate minimal geometry WASM core + browser-native UI/viewport before porting entire desktop window/GPU stack | Candidate architecture, not yet proven |
| ADR-005 | Exclude by build configuration/refactoring before deleting original sources | Working engineering policy |
