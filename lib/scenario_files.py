"""Keep required scenario artwork together, with legacy sidecar compatibility."""
from pathlib import Path


def scenario_asset_path(scenario, suffix):
    scenario = Path(scenario)
    path = scenario.parent / 'assets' / (scenario.name + suffix)
    legacy = Path(str(scenario) + suffix)
    return legacy if legacy.exists() and not path.exists() else path
