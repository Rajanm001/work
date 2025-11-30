# Contributing to Clinical Supply Chain Control Tower

Thank you for your interest in contributing to this project!

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Rajanm001/work.git
   cd clinical-supply-chain-ai
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   .\venv\Scripts\Activate.ps1  # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup database**
   ```bash
   python scripts/setup_complete.py
   ```

## Code Standards

### Python Style
- Follow PEP 8 guidelines
- Use type hints for function signatures
- Write docstrings for all public functions
- Maximum line length: 120 characters

### Example
```python
from typing import List, Dict, Any

def process_inventory(batches: List[Dict[str, Any]], threshold: int = 30) -> List[Dict[str, Any]]:
    """
    Filter inventory batches by expiry threshold.
    
    Args:
        batches: List of inventory batch dictionaries
        threshold: Number of days threshold for expiry (default: 30)
        
    Returns:
        List of batches expiring within threshold
    """
    return [b for b in batches if b['days_to_expiry'] <= threshold]
```

## Project Structure

```
clinical-supply-chain-ai/
├── agents/           # AI agent implementations
├── api/              # FastAPI REST API
├── database/         # Database setup and data
├── docs/             # Documentation
├── scripts/          # Automation scripts
├── tests/            # Test suite
├── tools/            # Reusable utilities
└── web/              # Frontend dashboard
```

## Testing

Run tests before submitting:

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=agents --cov=tools

# Validate project
python scripts/validate_project.py
```

## Submitting Changes

1. Create a feature branch
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit
   ```bash
   git add .
   git commit -m "Add: Brief description of changes"
   ```

3. Push to your fork
   ```bash
   git push origin feature/your-feature-name
   ```

4. Submit a Pull Request

## Commit Message Format

Use clear, descriptive commit messages:

- `Add:` - New features
- `Fix:` - Bug fixes
- `Update:` - Updates to existing features
- `Docs:` - Documentation changes
- `Test:` - Test additions or changes
- `Refactor:` - Code refactoring

Examples:
```
Add: Expiry prediction algorithm for batch monitoring
Fix: SQL query timeout in enrollment rate calculation
Update: Dashboard UI with real-time refresh
Docs: API endpoint documentation for inventory
```

## Code Review Process

All submissions require review. We look for:

- ✅ Code follows project standards
- ✅ Tests pass successfully
- ✅ Documentation is updated
- ✅ No breaking changes to existing functionality
- ✅ Performance impact is acceptable

## Questions?

For questions or discussions:
- Open an issue on GitHub
- Check existing documentation in `/docs`
- Review the [README.md](README.md)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing!** 🚀

*Maintained by Rajan Mishra*
