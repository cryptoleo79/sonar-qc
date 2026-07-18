"""Enable `python -m sonar_qc` as an equivalent to the `sonar-qc` console script."""
from .cli import main

raise SystemExit(main())
