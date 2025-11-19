import sys
import argparse
from pathlib import Path
from platformdirs import user_data_dir
import uvicorn
from litellm.proxy.proxy_server import app, save_worker_config

from .config import (
    default_config_path,
    load_config,
    list_profiles,
    get_default_profile,
    set_default_profile,
    get_profile_config,
    get_profile_config,
    setup_environment,
    ensure_config_exists,
)
from .utils import log, setup_tracer


def main():
    # Ensure configuration exists on first run
    ensure_config_exists()

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
        print("aiproxy 0.2.0")
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
    # If the path is absolute, use it directly.
    # If it's relative, check relative to the config file first (legacy/local dev),
    # then check in user_data_dir.
    litellm_config_path = Path(litellm_config_filename)

    if not litellm_config_path.is_absolute():
        config_dir = Path(args.config).parent.expanduser().resolve()
        potential_path = config_dir / litellm_config_filename

        if potential_path.exists():
            litellm_config_path = potential_path
        else:
            # Check user_data_dir
            data_dir = Path(user_data_dir("aiproxy"))
            litellm_config_path = data_dir / litellm_config_filename

    if not litellm_config_path.exists():
        print(
            f"ERROR: LiteLLM config file not found: {litellm_config_path}",
            file=sys.stderr,
        )
        # config_dir might not be defined if we didn't enter the if block above
        # but args.config is always defined
        config_dir_debug = Path(args.config).parent.expanduser().resolve()
        print(f"Config directory: {config_dir_debug}", file=sys.stderr)
        print(f"Expected file: {litellm_config_filename}", file=sys.stderr)
        sys.exit(1)

    # Set up tracer if enabled
    tracer_config = config.get("tracer", {})
    setup_tracer(tracer_config)

    # Configure LiteLLM
    save_worker_config(
        config=str(litellm_config_path),
    )

    log(f"Starting AI proxy on {host}:{port}")
    log(f"Using profile: {profile_name}")
    log(f"Using config: {args.config}")
    log(f"Using LiteLLM config: {litellm_config_path}")

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
