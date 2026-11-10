# Blender for Web

Blender for Web is a research project that brings selected Blender mesh operations to the browser. The current WebAssembly module can create a cube, extrude a face and transfer the resulting geometry to JavaScript. The timeline and engineering notes below document the work toward a browser-based modelling editor.

> Status: Phase 1.1 architecture complete; Phase 1.2 static dependency research and CI verified, with native OpenColorIO/CMake linker closure still blocked. Phase 1.3.1–1.3.4 isolated Blender-owned WASM feasibility, lifetime tests, mesh transfer and real-browser compatibility passed. Phase 2.1 component classification is complete; Phase 2.2 native core extraction and Phase 2.3 native stabilization remain unfinished.
>
> Source baseline: Blender **5.4 Alpha** (`BLENDER_VERSION 504`, cycle `alpha`), commit `67e5a5f874cf37e2a114cebd24f219d8c44a16ad`.
>
> This project deliberately retains the current alpha fork. It does **not** switch to an LTS release.

## Project timeline

| Phase | What changed |
| --- | --- |
| Starting point | Forked a pinned Blender 5.4 Alpha revision to investigate a browser-based modelling editor built on Blender’s geometry code. |
| Dependency audit | Mapped the BMesh, BKE and BLI paths needed for basic modelling and classified desktop subsystems that could be isolated from the browser target. |
| [Browser feasibility](https://github.com/bhargavkalita47/blender/commit/f8a1164b) | Compiled original Blender BMesh code to WebAssembly. Exercised cube creation, face extrusion, geometry transfer and repeated mesh creation and disposal in Chromium, Firefox and WebKit. |
| [Native extraction experiments](https://github.com/bhargavkalita47/blender/tree/dev/p2-2-completion) | Working branches link selected original Blender sources in a standalone native target. The cube and extrusion fixtures passed parity against a Blender executable built from the pinned source. |

**Today:** The integration branch contains the verified isolated WebAssembly path. Native extraction and broader modelling coverage are ongoing on working branches.

## Engineering challenges and solutions

- **Separating modelling from the desktop build.** The dependency audit distinguishes CMake target edges from source and symbol dependencies. An isolated BMesh target made it possible to test geometry without completing the full native build, where OpenColorIO configuration remains blocked.
- **Moving geometry across the WASM boundary.** A narrow C API exposes opaque mesh handles. The browser copies vertices and indices into JavaScript-owned buffers, and lifecycle tests repeatedly create and dispose of meshes.
- **Checking geometry against Blender.** Native extraction uses the same pinned source revision for the test target and Blender reference executable. Representative fixture comparisons make topology and geometry differences visible before broader extraction.

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
| 1.3 — Feasibility | Validate original Blender C++ in WASM, BMesh lifecycle, browser geometry transfer and runtime stability | WASM 1.3.1–1.3.4 verified; native configure/link baseline remains a tracked open gate |
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
- [1.3.1 — Blender BLI WASM smoke test (verified)](phase-1/1.3.1-bli-wasm.md)
- [1.3.2 — Original Blender BMesh creation/extrusion/lifecycle in WASM (verified)](phase-1/1.3.2-bmesh-wasm.md)
- [1.3.3 — Real-browser BMesh + copied geometry buffers (verified)](phase-1/1.3.3-browser-mesh.md)
- [1.3.4 — Performance, memory and three-browser compatibility (verified)](phase-1/1.3.4-stabilization.md)

## Evidence and limitations

Documented conclusions must distinguish **CMake target links**, **source include/symbol dependencies** and **actual runtime needs**. A target-level edge does not prove that a feature uses a dependency at runtime. Phase 1.1 documents verified representative source paths; it is **not** a file-by-file or link-tested dependency closure. Genuine Blender BLI and BMesh implementation files now compile, link and run as WebAssembly. The isolated BMesh port demonstrates cube creation, actual BMO face extrusion, safe repeated BMesh destruction, opaque handle isolation, JavaScript-owned vertex/index buffers, and execution in Chromium/Firefox/WebKit with matching geometry. The fixed-fixture stress benchmark has run in CI. These achievements do **not** demonstrate a complete extracted native Blender core, native CMake configuration, general polygon/UV editing, rendering, an interactive browser viewport, or production memory-safety/performance. The native OpenColorIO 2.3.0 configure blocker remains explicit.

### Architecture decision log

| ID | Decision | Status |
| --- | --- | --- |
| ADR-001 | Keep Blender 5.4 Alpha as source baseline, SHA above | Confirmed |
| ADR-002 | Protect `main`, integrate through `blender-for-web` | Confirmed |
| ADR-003 | Target a web editor centered on modeling, texturing and editing; defer advanced rendering/simulation/animation workflows | Working product boundary; refine in 2.1 |
| ADR-004 | Isolate original Blender BMesh geometry operations behind narrow WASM C ABI; retain browser-native UI/viewport | WASM engine/API feasibility verified, browser viewport not yet implemented |
| ADR-005 | Exclude by build configuration/refactoring before deleting original sources | Working engineering policy |
