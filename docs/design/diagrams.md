# Diagrams

~~~mermaid
flowchart LR
  subgraph Host[Host: Windows]
    C[Coordinator]:::svc
  end
  subgraph VM1[Agent VM #1]
    A1[Agent]:::svc
  end
  subgraph VM2[Agent VM #2]
    A2[Agent]:::svc
  end

  C -- REQ/REP --> A1
  C -- SUB/PUB --> A1
  C -- REQ/REP --> A2
  C -- SUB/PUB --> A2

classDef svc fill:#2b3a67,stroke:#98c1d9,color:#fff,rx:8,ry:8;
~~~

- Ports: input, capture, log events, ipc, telemetry, time.
- Adapters: win_input, dx_capture, ocr_tesseract, ipc_zmq.
