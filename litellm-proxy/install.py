#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pyyaml",
# ]
# ///

import yaml
from pathlib import Path
import os


def init_config():
    """Initialize litellm-proxy configuration files."""

    # Set up config file path
    config_dir = Path.home() / ".config" / "litellm-proxy"
    config_file = config_dir / "config.yaml"

    print(f"Creating config directory: {config_dir}")

    # Create directory if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)

    # Create default config if it doesn't exist
    if not config_file.exists():
        print(f"Creating default config file: {config_file}")

        # Create default proxy config.yaml
        proxy_config = {
            "litellm-config": "litellm-config.yaml",
            "tracer": {"enabled": False},
        }

        with open(config_file, "w") as f:
            yaml.dump(proxy_config, f, default_flow_style=False)

        # Create default litellm config file
        litellm_config_file = config_dir / "proxy.yaml"
        litellm_config = {
            "model_list": [
                {
                    "model_name": "xplatform3",
                    "litellm_params": {
                        "model": "openai/xplatform3",
                        "api_key": os.getenv("XPLATFORM3_API_KEY"),
                        "api_base": "https://api.xplatform.ai/v1",
                    },
                }
            ],
            "general_settings": {"database_url": "sqlite:///./litellm.db"},
        }

        print(f"Creating default litellm config file: {litellm_config_file}")
        with open(litellm_config_file, "w") as f:
            yaml.dump(litellm_config, f, default_flow_style=False)

        print("✅ Configuration files created successfully!")
        print(f"📁 Config location: {config_dir}")
        print(f"📝 Main config: {config_file}")
        print(f"⚙️  LiteLLM config: {litellm_config_file}")

    else:
        print(f"✅ Config already exists: {config_file}")

    return config_file, config_dir


if __name__ == "__main__":
    init_config()
