# Contributing to Sentinel

First off, thank you for considering contributing to Sentinel! 🎉 Every contribution helps make attendance tracking better for teams worldwide.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Commit Message Format](#commit-message-format)
- [Pull Request Process](#pull-request-process)
- [Testing](#testing)

---

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to [seejawad556@gmail.com](mailto:seejawad556@gmail.com).

---

## How Can I Contribute?

### 🐛 Reporting Bugs

Before submitting a bug, please check [existing issues](https://github.com/jawad-ahmad1/sentinel-attendance/issues) to avoid duplicates.

When filing a bug, use the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.md) and include:

- Clear title and description
- Steps to reproduce
- Expected vs actual behavior
- Screenshots (if UI-related)
- Environment details (OS, browser, version)

### 💡 Suggesting Features

Feature requests are welcome! Use the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.md) and describe:

- The problem you're trying to solve
- Your proposed solution
- Who would benefit

### 🔧 Code Contributions

1. Look for issues labeled `good first issue` or `help wanted`
2. Comment on the issue to indicate you're working on it
3. Follow the development setup and coding standards below

### 📝 Documentation Improvements

Documentation fixes are always welcome — typos, clarifications, new examples. No issue needed for small doc fixes.

---

## Development Setup

### Prerequisites

- Python 3.12+
- PostgreSQL 16+ (or Docker)
- Redis 7+ (or Docker)
- Git

### Local Setup

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/sentinel-attendance.git
cd sentinel-attendance

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: .\venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt
pip install pylint mypy bandit black isort  # Dev tools

# 4. Configure environment
cp .env.example .env
# Edit .env with your database credentials

# 5. Start dependencies (via Docker)
docker compose up -d db redis

# 6. Run the app
uvicorn app.main:app --reload --port 8000

# 7. Run tests
python -m pytest tests/ -v
```

### Docker Setup

```bash
docker compose up -d --build
```

---

## Coding Standards

### Python Style

- **Formatter:** [Black](https://github.com/psf/black) (line-length 99)
- **Import Sorting:** [isort](https://pycqa.github.io/isort/) (profile: black)
- **Linting:** Pylint (disable C,R conventions → target 9.5+/10)
- **Type Checking:** Mypy (ignore-missing-imports)
- **Security:** Bandit (zero Medium/High findings)

### Before Committing

```bash
# Format code
black app tests --line-length 99
isort app tests --profile black --line-length 99

# Lint
pylint app --disable=C,R
flake8 app --select=F --count
bandit -r app -ll

# Type check
mypy app --ignore-missing-imports

# Test
python -m pytest tests/ -v
```

### Code Principles

- Use **async/await** for all database and network operations
- Use **Pydantic schemas** for all request/response validation
- Use **dependency injection** (`Depends()`) for auth and DB sessions
- Follow **FastAPI patterns** — router → endpoint → service → repository
- Add **docstrings** to all public functions
- Use **type hints** on all function signatures

---

## Commit Message Format

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation only changes |
| `style` | Formatting, missing semicolons, etc. |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `perf` | Performance improvement |
| `test` | Adding or correcting tests |
| `chore` | Maintenance tasks (deps, CI, etc.) |

### Examples

```
feat(reports): add monthly absence report endpoint
fix(scan): prevent duplicate scans under concurrent requests
docs(readme): update quick start guide for Docker v2
refactor(auth): replace mutable default with Field(default_factory)
test(employees): add soft-delete integration test
```

---

## Pull Request Process

1. **Branch:** Create a feature branch from `main`
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Develop:** Make your changes following the coding standards

3. **Test:** Ensure all tests pass
   ```bash
   python -m pytest tests/ -v
   ```

4. **Format:** Run Black + isort before committing
   ```bash
   black app tests --line-length 99
   isort app tests --profile black --line-length 99
   ```

5. **Commit:** Use conventional commit messages

6. **Push:** Push your branch
   ```bash
   git push origin feature/my-feature
   ```

7. **PR:** Open a Pull Request using the [PR template](.github/PULL_REQUEST_TEMPLATE.md)

8. **Review:** Address any review feedback

9. **Merge:** A maintainer will merge your PR once approved

### PR Requirements

- [ ] All tests pass
- [ ] No new Pylint/Flake8/Bandit warnings
- [ ] Code formatted with Black + isort
- [ ] Documentation updated (if applicable)
- [ ] PR description clearly explains changes

---

## Testing

### Running Tests

```bash
# Full suite
python -m pytest tests/ -v

# Specific file
python -m pytest tests/test_scan.py -v

# With coverage
python -m pytest tests/ --cov=app --cov-report=html
```

### Writing Tests

- Place tests in `tests/` directory
- Name files `test_*.py`
- Use `pytest-asyncio` for async tests
- Use the `client` and `db_session` fixtures from `conftest.py`
- Aim for both happy-path and error-path coverage

### Test Structure

```python
@pytest.mark.asyncio
async def test_scan_creates_attendance(client, db_session):
    """Scanning a registered card should create an IN event."""
    # Arrange
    employee = await create_test_employee(db_session)

    # Act
    response = await client.post("/api/v1/scan", json={"uid": employee.uid})

    # Assert
    assert response.status_code == 200
    assert response.json()["event_type"] == "IN"
```

---

## 🙏 Thank You!

Your contributions make Sentinel better for everyone. Whether it's a bug fix, feature, docs improvement, or just a typo fix — it all matters.

**Happy coding!** 🎉

---

[← Back to README](README.md)
