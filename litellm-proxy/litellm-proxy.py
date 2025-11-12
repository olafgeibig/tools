#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "litellm[proxy]",
#     "arize-phoenix-otel",
#     "openinference-instrumentation-litellm",
#     "uvicorn",
# ]
# ///
from phoenix.otel import register
import uvicorn
from litellm.proxy.proxy_server import app, save_worker_config
import os

os.environ["XPLATFORM1_API_KEY"]="f49d40df888e410e8163864774d76638"
os.environ["XPLATFORM3_API_KEY"]="ef25b5ad010a47668dcf38be6f07491c"
os.environ["PHOENIX_API_KEY"]="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJBcGlLZXk6MSJ9.GZfE6ZIHvzDGG32iDnBN2-QN-jLgF1XxtH0m1di6ATY"

# Set up tracing instrumentation
tracer_provider = register(
    project_name="xplatform-proxy",
    auto_instrument=True,
    endpoint="https://phoenix.lttm26.de/v1/traces",
    batch=True,
)

save_worker_config(
    config="./xplatform3.yaml",  # Your config file
    # Add other parameters as needed
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=4000)