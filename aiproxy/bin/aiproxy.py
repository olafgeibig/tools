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
    """Use SCRIPT_CONFIG env var from Homebrew or fallback to user config"""
    return (
        os.environ.get("SCRIPT_CONFIG")
        or os.environ.get("AIPROXY_CONFIG")
        or "~/.config/aiproxy/config.yaml"
    )


def log(message):
    print(f"[aiproxy] {message}", flush=True)


def load_config(config_path):
    """Load and validate configuration from YAML file"""
    import yaml

    if not os.path.exists(config_path):
        print(f"ERROR: Configuration file not found: {config_path}", file=sys.stderr)
        print(
            f"Create it from example or run: aiproxy --config-dir",
            file=sys.stderr,
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

        project_name = tracer_config.get("project_name", "aiproxy")
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


def list_profiles(config):
    """List all available profiles with descriptions"""
    profiles = config.get("profiles", {})
    default_profile = config.get("default_profile")

    if not profiles:
        print("No profiles found in configuration", file=sys.stderr)
        return False

    print("Available profiles:")
    for name, profile_config in profiles.items():
        description = profile_config.get("description", "No description available")
        default_marker = " (default)" if name == default_profile else ""
        print(f"  {name}{default_marker}")
        print(f"    {description}")
        print(f"    litellm-config: {profile_config.get('litellm-config', 'N/A')}")
        print(f"    host: {profile_config.get('host', 'N/A')}")
        print(f"    port: {profile_config.get('port', 'N/A')}")
        print()

    return True


def get_default_profile(config):
    """Get the current default profile name"""
    default_profile = config.get("default_profile")
    if default_profile:
        print(f"Default profile: {default_profile}")
    else:
        print("No default profile set", file=sys.stderr)
    return default_profile


def set_default_profile(config_path, profile_name):
    """Set the default profile in the config file"""
    import yaml

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f) or {}

        profiles = config.get("profiles", {})
        if profile_name not in profiles:
            print(f"ERROR: Profile '{profile_name}' not found", file=sys.stderr)
            print("Available profiles:", file=sys.stderr)
            for name in profiles.keys():
                print(f"  {name}", file=sys.stderr)
            return False

        config["default_profile"] = profile_name

        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)

        print(f"Default profile set to: {profile_name}")
        return True
    except Exception as e:
        print(f"ERROR: Could not update config: {e}", file=sys.stderr)
        return False


def get_profile_config(config, profile_name):
    """Get configuration for a specific profile"""
    profiles = config.get("profiles", {})

    if profile_name not in profiles:
        print(f"ERROR: Profile '{profile_name}' not found", file=sys.stderr)
        print("Use --list-profiles to see available profiles", file=sys.stderr)
        return None

    profile_config = profiles[profile_name]

    # Validate required fields
    required_fields = ["litellm-config", "host", "port"]
    for field in required_fields:
        if field not in profile_config:
            print(
                f"ERROR: Profile '{profile_name}' missing required field: {field}",
                file=sys.stderr,
            )
            return None

    return profile_config


def check_legacy_config(config):
    """Check for legacy aiproxy section and suggest migration"""
    if "aiproxy" in config:
        print("WARNING: Legacy 'aiproxy' configuration section found.", file=sys.stderr)
        print("Please migrate to the new profile-based format:", file=sys.stderr)
        print("  https://github.com/your-repo/docs/migration", file=sys.stderr)
        print("", file=sys.stderr)
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description="AI Proxy Server")
    parser.add_argument(
        "--config",
        default=default_config_path(),
        help="Path to config file (default: AIPROXY_CONFIG or ~/.config/aiproxy/config.yaml)",
    )
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    parser.add_argument(
        "--config-dir",
        action="store_true",
        help="Output absolute path to config directory",
    )
    parser.add_argument("--profile", help="Profile to use (overrides default profile)")
    parser.add_argument(
        "--list-profiles",
        action="store_true",
        help="List all available profiles",
    )
    parser.add_argument(
        "--get-default",
        action="store_true",
        help="Show current default profile",
    )
    parser.add_argument(
        "--set-default",
        metavar="PROFILE",
        help="Set default profile",
    )
    parser.add_argument("--host", help="Override host from profile")
    parser.add_argument("--port", type=int, help="Override port from profile")
    args = parser.parse_args()

    if args.version:
        print("aiproxy 1.0.0")
        sys.exit(0)

    if args.config_dir:
        config_path = args.config or default_config_path()
        config_dir = Path(config_path).parent.expanduser().resolve()
        print(config_dir)
        sys.exit(0)

    # Load configuration
    config = load_config(args.config)

    # Handle profile management commands
    if args.list_profiles:
        list_profiles(config)
        sys.exit(0)

    if args.get_default:
        get_default_profile(config)
        sys.exit(0)

    if args.set_default:
        if set_default_profile(args.config, args.set_default):
            sys.exit(0)
        else:
            sys.exit(1)

    # Check for legacy configuration
    check_legacy_config(config)

    # Determine which profile to use
    profile_name = args.profile or config.get("default_profile")
    if not profile_name:
        print("ERROR: No profile specified and no default profile set", file=sys.stderr)
        print("Use --profile <name> or set default_profile in config", file=sys.stderr)
        print("Use --list-profiles to see available profiles", file=sys.stderr)
        sys.exit(1)

    # Get profile configuration
    profile_config = get_profile_config(config, profile_name)
    if not profile_config:
        sys.exit(1)

    # Set up environment
    setup_environment(config)

    # Extract profile settings
    litellm_config_filename = profile_config["litellm-config"]
    host = args.host or profile_config["host"]
    port = args.port or profile_config["port"]

    # Resolve litellm config path
    config_dir = Path(args.config).parent.expanduser().resolve()
    litellm_config_path = config_dir / litellm_config_filename

    if not litellm_config_path.exists():
        print(
            f"ERROR: LiteLLM config file not found: {litellm_config_path}",
            file=sys.stderr,
        )
        print(f"Config directory: {config_dir}", file=sys.stderr)
        print(f"Expected file: {litellm_config_filename}", file=sys.stderr)
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

    log(f"Starting AI proxy on {host}:{port}")
    log(f"Using profile: {profile_name}")
    log(f"Using config: {args.config}")
    log(f"Using LiteLLM config: {litellm_config_path}")

    if __name__ == "__main__":
        uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
