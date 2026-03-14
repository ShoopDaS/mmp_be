# Tests

```bash
pytest                                      # all tests
pytest tests/unit/                          # unit only
pytest --cov=src --cov-report=html          # coverage report
```

- Uses `pytest-asyncio` for async handlers
- Uses `moto` for DynamoDB mocking
- Test files live in `tests/unit/` mirroring `src/` structure
- `tests/integration/` exists but is empty
