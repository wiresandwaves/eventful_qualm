def test_imports():
    # Basic import smoke to catch packaging/import path issues
    import adapters.ipc_inproc  # noqa: F401
    import adapters.ipc_zmq  # noqa: F401
    import ports.ipc  # noqa: F401

    import apps.agent.compose  # noqa: F401
    import apps.coordinator.compose  # noqa: F401
