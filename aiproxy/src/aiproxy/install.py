import sys
from pathlib import Path
from platformdirs import user_config_dir, user_log_dir, user_data_dir
from importlib.resources import files
import getpass
import shutil


def ensure_installation():
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


def install_service():
    """Install the aiproxy service as a LaunchAgent (per-user)"""
    import os
    import subprocess

    # Determine user without requiring root
    user = getpass.getuser()

    # Find the aiproxy executable on PATH for current user
    aiproxy_path = shutil.which("aiproxy")
    if not aiproxy_path:
        print(f"ERROR: Could not find 'aiproxy' executable for user {user}.")
        sys.exit(1)

    print(f"Found aiproxy at: {aiproxy_path}")

    # Determine log file locations using platformdirs
    log_dir = Path(user_log_dir("aiproxy"))
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = str(log_dir / "aiproxy.launchd.out.log")
    stderr_path = str(log_dir / "aiproxy.launchd.err.log")

    # Read the template
    try:
        package_files = files("aiproxy")
        plist_template = (
            package_files / "share" / "com.github.olafgeibig.tools.aiproxy.plist"
        ).read_text()
    except Exception as e:
        print(f"ERROR: Could not read plist template: {e}")
        sys.exit(1)

    # Fill in the template
    plist_content = plist_template.replace("{{AIPROXY_PATH}}", aiproxy_path)
    plist_content = plist_content.replace("{{STDOUT_PATH}}", stdout_path)
    plist_content = plist_content.replace("{{STDERR_PATH}}", stderr_path)

    # Write LaunchAgent plist to ~/Library/LaunchAgents
    agent_dir = Path.home() / "Library" / "LaunchAgents"
    agent_dir.mkdir(parents=True, exist_ok=True)
    agent_plist = agent_dir / "com.github.olafgeibig.tools.aiproxy.plist"
    try:
        agent_plist.write_text(plist_content)
        print(f"Created LaunchAgent plist at {agent_plist}")
    except Exception as e:
        print(f"ERROR: Could not write plist file: {e}")
        sys.exit(1)

    # Load via modern launchctl commands
    uid = os.getuid()
    label = "com.github.olafgeibig.tools.aiproxy"

    # bootstrap registers the agent
    result_bootstrap = subprocess.run(
        ["launchctl", "bootstrap", f"gui/{uid}", str(agent_plist)],
        capture_output=True,
        text=True,
    )

    if result_bootstrap.returncode != 0:
        # If already loaded, bootstrap may fail; continue to enable/kickstart
        print(f"WARNING: bootstrap failed: {result_bootstrap.stderr.strip()}")

    # ensure enabled
    result_enable = subprocess.run(
        ["launchctl", "enable", f"gui/{uid}/{label}"], capture_output=True, text=True
    )

    if result_enable.returncode != 0:
        print(f"WARNING: enable failed: {result_enable.stderr.strip()}")

    # start now
    result_kick = subprocess.run(
        ["launchctl", "kickstart", "-k", f"gui/{uid}/{label}"],
        capture_output=True,
        text=True,
    )

    if result_kick.returncode != 0:
        print(f"ERROR: kickstart failed: {result_kick.stderr.strip()}")
        sys.exit(1)

    print("LaunchAgent installed, enabled, and started.")


def uninstall_service():
    """Uninstall the aiproxy LaunchAgent (per-user)"""
    import os
    import subprocess

    uid = os.getuid()
    label = "com.github.olafgeibig.tools.aiproxy"
    agent_plist = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"

    # Attempt to bootout (unload) the agent
    result_bootout = subprocess.run(
        ["launchctl", "bootout", f"gui/{uid}/{label}"], capture_output=True, text=True
    )
    if result_bootout.returncode != 0:
        print(f"WARNING: bootout failed: {result_bootout.stderr.strip()}")

    # Remove the plist file if it exists
    try:
        if agent_plist.exists():
            agent_plist.unlink()
            print(f"Removed LaunchAgent plist at {agent_plist}")
        else:
            print("LaunchAgent plist not found; nothing to remove.")
    except Exception as e:
        print(f"ERROR: Failed to remove plist: {e}")
        sys.exit(1)

    print("LaunchAgent uninstalled.")


def restart_service():
    """Restart the aiproxy LaunchAgent (per-user)"""
    import os
    import subprocess

    uid = os.getuid()
    label = "com.github.olafgeibig.tools.aiproxy"
    agent_plist = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"

    # Try kickstart to restart immediately
    result_kick = subprocess.run(
        ["launchctl", "kickstart", "-k", f"gui/{uid}/{label}"],
        capture_output=True,
        text=True,
    )

    if result_kick.returncode == 0:
        print("LaunchAgent restarted.")
        return

    # If kickstart failed, attempt to bootstrap then kickstart if plist exists
    if not agent_plist.exists():
        print("ERROR: LaunchAgent plist not found. Run --install-service first.")
        sys.exit(1)

    result_bootstrap = subprocess.run(
        ["launchctl", "bootstrap", f"gui/{uid}", str(agent_plist)],
        capture_output=True,
        text=True,
    )
    if result_bootstrap.returncode != 0:
        print(f"ERROR: bootstrap failed: {result_bootstrap.stderr.strip()}")
        sys.exit(1)

    result_enable = subprocess.run(
        ["launchctl", "enable", f"gui/{uid}/{label}"], capture_output=True, text=True
    )
    if result_enable.returncode != 0:
        print(f"WARNING: enable failed: {result_enable.stderr.strip()}")

    result_kick2 = subprocess.run(
        ["launchctl", "kickstart", "-k", f"gui/{uid}/{label}"],
        capture_output=True,
        text=True,
    )
    if result_kick2.returncode != 0:
        print(f"ERROR: kickstart failed: {result_kick2.stderr.strip()}")
        sys.exit(1)

    print("LaunchAgent bootstrapped and restarted.")
