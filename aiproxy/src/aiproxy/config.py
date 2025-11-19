import os
import sys
from pathlib import Path
from platformdirs import user_config_dir
import yaml
from .utils import log
import shutil
from importlib.resources import files


def default_config_path():
    """Use user config dir for configuration"""
    config_dir = Path(user_config_dir("aiproxy"))
    return str(config_dir / "config.yaml")


def ensure_config_exists():
    """Ensure configuration files exist in the user config directory"""
    config_dir = Path(user_config_dir("aiproxy"))
    config_path = config_dir / "config.yaml"

    if not config_path.exists():
        print(f"First run detected. Initializing configuration at {config_dir}...")
        config_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Access package data using importlib.resources.files
            package_files = files("aiproxy")
            etc_dir = package_files / "etc"

            # Copy config.yaml
            config_file = etc_dir / "config.yaml"
            if config_file.is_file():
                config_path.write_text(config_file.read_text())
                print(f"Created {config_path}")
            else:
                print(
                    "WARNING: Default config.yaml not found in package.",
                    file=sys.stderr,
                )

            # Copy example.yaml if it exists
            example_file = etc_dir / "example.yaml"
            if example_file.is_file():
                (config_dir / "example.yaml").write_text(example_file.read_text())
                print(f"Created {config_dir / 'example.yaml'}")

        except Exception as e:
            print(f"ERROR: Failed to initialize configuration: {e}", file=sys.stderr)
            # We don't exit here, we let load_config fail if it must, or return empty


def load_config(config_path):
    """Load and validate configuration from YAML file"""
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
