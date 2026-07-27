# orc — GRACE Orchestrator

Automated execution engine for the strict GRACE methodology.
Reads artifacts, generates controller packets, executes them via LLM,
checks scope and verification, commits results.

## Architecture

```
development-plan.xml
       |
       v
  artifact_loader ---> controller (packet generation)
                              |
                              v
                     LLMWorker (OpenAI API -> code)
                              |
                              v
                     reviewer (scope + verification)
                              |
                     +--------+--------+
                     | PASSED          | FAILED
                     v                 v
               git commit       repair loop (x3)
                     |                 |
                     v                 v
               next wave        failure packet
```

## Quickstart

```bash
git clone https://github.com/Av75057/orc.git
cd orc
export OPENAI_API_KEY="sk-..."
python -m smart_home.main
python -m pytest tests/test_*.py -v
```

## Test Project: Smart Home

- `src/smart_home/` — EventBus, sensors, actuators, controller
- `docs/` — requirements, technology, development plan, knowledge graph, verification matrix

## License

MIT

