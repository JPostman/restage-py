# ReStage Python

A runnable of the ReStage execution model for Python. It uses decorators, dependency resolution, shared runtime state, and pluggable request executors while relying only on the Python standard library.

## Decorator model

```python
from restage_py import Collection, MockExecutor, ReStage, RequestSpec

restage = ReStage()

@restage.request(
    id="login",
    namespace="product",
    folder="Auth",
    request="Login user and get tokens",
)
def login(ctx):
    ctx.request.body["username"] = "python-user"

@restage.response(
    id="Ref1",
    depends_on="#login",
    request="Get current authenticated user",
    verify=200,
)
def current_user(ctx):
    token = ctx.dependency("#login").response.body["accessToken"]
    ctx.variables["accessToken"] = token

@restage.runner(id="authFlow", depends_on="#Ref1")
def auth_flow(ctx):
    return "complete"
```

## Included behavior

- `@restage.request`, `@restage.response`, `@restage.runner`, and `@restage.call`
- Dependency references by function name or `#id`
- Namespace and folder inheritance from dependencies
- Dependency ordering with one execution per session
- Cycle detection
- Request mutation before execution
- Hard verification before the function body
- Soft verification after the function body
- Hard and aggregated soft assertions
- Shared variables and dependency-result lookup
- Mock executor and a basic `urllib` HTTP executor
- CLI entry point, examples, and tests

## Run without installation

From the project root:

```bash
PYTHONPATH=src python examples/auth_flow.py
```

Expected output:

```text
flow complete
['#login', '#Ref1', '#authFlow']
```

## Run tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Install locally

```bash
python -m pip install -e .
```

Then run a module that exposes a `runtime` object:

```bash
restage-py examples.auth_flow '#authFlow'
```

## Suggested next phase

For a production implementation, separate the shared language-neutral ReStage model from the Python adapter. The adapter can parse and modify decorators with Python's `ast` module, while the runtime can integrate with `pytest` and an HTTP client such as `httpx` or `requests`.
