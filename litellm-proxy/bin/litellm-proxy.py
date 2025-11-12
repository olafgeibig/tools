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

import os
import sys
import argparse
from pathlib import Path


def default_config_path():
    """Use dedicated config environment variable or fallback to user config"""
    return (
        os.environ.get("LITELLM_PROXY_CONFIG") or "~/.config/litellm-proxy/config.yaml"
    )


def log(message):
    print(f"[litellm-proxy] {message}", flush=True)


def load_config(config_path):
    """Load and validate configuration from YAML file"""
    import yaml

    if not os.path.exists(config_path):
        print(f"ERROR: Configuration file not found: {config_path}", file=sys.stderr)
        print(
            f"Create it from the example or run: litellm-proxy --edit", file=sys.stderr
        )
        sys.exit(1)

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}
        return config
    except Exception as e:
        print(f"ERROR: Could not read config at {config_path}: {e}", file=sys.stderr)
        sys.exit(1)


def setup_environment(config):
    """Set up environment variables from config"""
    env_config = config.get("env", {})
    for key, value in env_config.items():
        if value:
            # Set direct value from config (e.g., "API_KEY: your-api-key-here")
            os.environ[key] = str(value)
            log(
                f"Set {key} from config: {str(value)[:20]}{'...' if len(str(value)) > 20 else ''}"
            )


def setup_tracer(tracer_config):
    """Set up tracing if enabled"""
    if not tracer_config.get("enabled", False):
        return None

    try:
        from phoenix.otel import register

        project_name = tracer_config.get("project_name", "litellm-proxy")
        endpoint = tracer_config.get("endpoint")

        if not endpoint:
            print("WARNING: Tracer enabled but no endpoint specified", file=sys.stderr)
            return None

        tracer_provider = register(
            project_name=project_name,
            auto_instrument=True,
            endpoint=endpoint,
            batch=True,
        )
        log(f"Tracing enabled for project: {project_name}")
        return tracer_provider
    except ImportError:
        print(
            "WARNING: Phoenix dependencies not available, tracing disabled",
            file=sys.stderr,
        )
        return None
    except Exception as e:
        print(f"WARNING: Failed to setup tracer: {e}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="LiteLLM Proxy Server")
    parser.add_argument(
        "--config",
        default=default_config_path(),
        help="Path to config file (default: LITELLM_PROXY_CONFIG or ~/.config/litellm-proxy/config.yaml)",
    )
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    parser.add_argument(
        "--edit", action="store_true", help="Open config file in default editor"
    )
    parser.add_argument("--host", help="Override host from config")
    parser.add_argument("--port", type=int, help="Override port from config")
    args = parser.parse_args()

    if args.version:
        print("litellm-proxy 1.0.0")
        sys.exit(0)

    if args.edit:
        import subprocess
        import shutil

        config_path = args.config or default_config_path()

        # Ensure config file exists
        if not os.path.exists(config_path):
            example_path = config_path.replace(".yaml", ".yaml.example")
            if os.path.exists(example_path):
                shutil.copy(example_path, config_path)
                os.chmod(config_path, 0o600)
                print(f"Created config file from example: {config_path}")
            else:
                print(
                    f"ERROR: Example config not found at {example_path}",
                    file=sys.stderr,
                )
                sys.exit(1)

        editor = os.environ.get("VISUAL") or os.environ.get("EDITOR", "nano")
        try:
            subprocess.call([editor, config_path])
        except FileNotFoundError:
            print(
                f"ERROR: Editor '{editor}' not found. Please set VISUAL or EDITOR environment variable or install nano.",
                file=sys.stderr,
            )
            sys.exit(1)
        sys.exit(0)

    # Load configuration
    config = load_config(args.config)

    # Set up environment
    setup_environment(config)

    # Get proxy configuration
    proxy_config = config.get("litellm-proxy", {})
    litellm_config_filename = proxy_config.get("config", "litellm.yaml")
    host = args.host or proxy_config.get("host", "0.0.0.0")
    port = args.port or proxy_config.get("port", 4000)

    # Resolve litellm config path
    config_dir = Path(args.config).parent
    litellm_config_path = config_dir / litellm_config_filename

    if not litellm_config_path.exists():
        print(
            f"ERROR: LiteLLM config file not found: {litellm_config_path}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Set up tracer if enabled
    tracer_config = config.get("tracer", {})
    setup_tracer(tracer_config)

    # Import heavy dependencies only after argument parsing
    import uvicorn
    from litellm.proxy.proxy_server import app, save_worker_config

    # Configure LiteLLM
    save_worker_config(
        config=str(litellm_config_path),
    )

    log(f"Starting LiteLLM proxy on {host}:{port}")
    log(f"Using config: {args.config}")
    log(f"Using LiteLLM config: {litellm_config_path}")

    if __name__ == "__main__":
        uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
