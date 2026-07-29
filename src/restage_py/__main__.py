from __future__ import annotations

import argparse
import importlib
import sys

from .api import ReStage


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a ReStage Python prototype node from a module."
    )
    parser.add_argument("module", help="Importable module containing a `runtime` object")
    parser.add_argument("reference", help="Function name or #id to execute")
    args = parser.parse_args()

    module = importlib.import_module(args.module)
    runtime = getattr(module, "runtime", None)
    if runtime is None:
        parser.error(f"Module {args.module!r} does not expose a `runtime` object.")
    record = runtime.run(args.reference)
    print(f"Executed: {record.metadata.canonical_reference}")
    if record.response is not None:
        print(f"Status: {record.response.status_code}")
        print(f"Body: {record.response.body!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
