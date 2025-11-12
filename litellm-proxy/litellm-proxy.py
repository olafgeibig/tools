#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "litellm[proxy]",
#     "arize-phoenix-otel",
#     "openinference-instrumentation-litellm",
#     "uvicorn",
#     "pyyaml",
# ]
# ///
from phoenix.otel import register
import uvicorn
from litellm.proxy.proxy_server import app, save_worker_config
import os
import yaml
from pathlib import Path

os.environ["XPLATFORM1_API_KEY"] = "f49d40df888e410e8163864774d76638"
os.environ["XPLATFORM3_API_KEY"] = "ef25b5ad010a47668dcf38be6f07491c"
os.environ["PHOENIX_API_KEY"] = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJBcGlLZXk6MSJ9.GZfE6ZIHvzDGG32iDnBN2-QN-jLgF1XxtH0m1di6ATY"
)


# Check if config exists
config_dir = Path.home() / ".config" / "litellm-proxy"
config_file = config_dir / "config.yaml"

if not config_file.exists():
    print(
        "❌ Configuration file not found. Please ensure the installation script has been run."
    )
    print(f"Expected location: {config_file}")
    exit(1)

# Load proxy config
with open(config_file, "r") as f:
    proxy_config = yaml.safe_load(f)

# Get litellm config filename and tracer settings
litellm_config_filename = proxy_config.get("litellm-config", "litellm-config.yaml")
tracer_config = proxy_config.get("tracer", {})
tracer_enabled = tracer_config.get("enabled", False)

# Set up litellm config path
config_dir = config_file.parent
litellm_config_path = config_dir / litellm_config_filename

# Ensure litellm config file exists
if not litellm_config_path.exists():
    raise FileNotFoundError(f"Litellm config file not found: {litellm_config_path}")

# Enable/disable tracing based on config
if tracer_enabled:
    tracer_provider = register(
        project_name="xplatform-proxy",
        auto_instrument=True,
        endpoint="https://phoenix.lttm26.de/v1/traces",
        batch=True,
    )

save_worker_config(
    config=str(litellm_config_path),  # Use litellm config from proxy config
    # Add other parameters as needed
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4000)
