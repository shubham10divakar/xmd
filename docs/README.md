# XMD Docs

Design history and vision behind the runtime. For *using* XMD, start with the
[main README](../README.md); for the precise current contract, see
[`SPEC-v0.0.2.md`](../SPEC-v0.0.2.md).

| Doc | What it is |
|-----|-----------|
| [architecture.md](./architecture.md) | The original XRuntime architecture — the 7 layers (parser → IR → execution → plugins → memory → events → agent) and the v0.1→v1.0 roadmap. |
| [vision.md](./vision.md) | Strategic direction: the three paths considered (IPython-for-Markdown / Docker-for-Documents / OS-for-Documents), the phased build strategy, and the long-term XOS platform vision. |
| [discussion-2026-05-30.md](./discussion-2026-05-30.md) | The build-decision log: the agent-native wedge, inline-first, "any language / don't bundle interpreters," collapsing 13 extensions into one `.xmd`, the three memory powers, the field-ownership fix, and the v0.0.1 → v0.0.2 scope. |

> These describe intent and the road traveled. Where a doc and the SPEC disagree,
> **the SPEC is authoritative** for what the code actually does today.
