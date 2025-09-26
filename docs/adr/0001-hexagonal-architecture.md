# ADR 0001 — Hexagonal Architecture (Ports & Adapters)

- Status: Accepted
- Date: 2025-09-24
- Deciders: Project Owner
- Tags: architecture, structure

## Context
We want a professional, testable design that cleanly separates game-facing details (Windows input, screen capture) from decision logic (state machines/BT, rules). We also want to swap infrastructure (e.g., ZMQ vs gRPC, dxcam vs mss) without touching core logic.

## Decision
Adopt hexagonal architecture:
- Domain (core): pure Python logic (HFSM/BT, policies).
- Ports (interfaces): input, capture, OCR, logs, IPC, time/clock, telemetry.
- Adapters: concrete implementations (Win SendInput, dxcam/mss, Tesseract, ZMQ/gRPC).
- Apps: thin composition layers for the agent and the coordinator.

## Consequences
- Positive: High testability; domain runs with fakes. Infra can change without refactoring domain.
- Negative: Upfront cost defining interfaces and composition; more packages to manage.

## Alternatives Considered
- Monolithic scripts: fast start, hard to test/maintain — rejected.
- Layered MVC: some separation but infra concerns leak into core — rejected.
