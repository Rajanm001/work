# Test Suite for Clinical Supply Chain AI

## Running Tests

```powershell
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=agents --cov=tools --cov=api

# Run specific test file
pytest tests/test_database.py -v
```

## Test Categories

- `test_database.py` - Database connection and query tests
- `test_agents.py` - Agent functionality tests
- `test_api.py` - API endpoint tests
- `test_tools.py` - Tool function tests

## Writing Tests

Follow pytest conventions:
```python
def test_example():
    assert True
```
