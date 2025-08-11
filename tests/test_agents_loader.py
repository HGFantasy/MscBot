def test_load_agents_and_emit():
    from agents import emit, iter_active_agents, load_agents

    load_agents()
    list(iter_active_agents())
    # Should not crash even if zero agents are active; emit returns a dict when collect=True
    results = None
    results2 = None
    try:
        results = __import__("asyncio").run(emit("start", collect=True))
        results2 = __import__("asyncio").run(emit("start", collect=True))
    except RuntimeError:
        # In case of already running loop in some envs, fallback
        loop = __import__("asyncio").new_event_loop()
        try:
            results = loop.run_until_complete(emit("start", collect=True))
            results2 = loop.run_until_complete(emit("start", collect=True))
        finally:
            loop.close()
    assert isinstance(results, dict)
    assert isinstance(results2, dict)
