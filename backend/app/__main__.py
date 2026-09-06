"""Allow `python -m app` to invoke the CLI."""

from app.cli import main

raise SystemExit(main())
