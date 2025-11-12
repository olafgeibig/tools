# Concept: Managing Personal **UV** Scripts as Homebrew Services

This document outlines a professional architecture for managing a personal executable (like your `kube-backup` Python script) as a launchd **LaunchAgent**, fully managed by **Homebrew**, with **UV** handling Python execution and dependencies. No Homebrew Python or venvs are required—each script is self-contained via `uv run --script`.

You get:

- **A Single Command:** `brew services start kube-backup`
- **Version Control:** `brew upgrade kube-backup`
- **Clean Separation:** Your script's code lives in one repo, and its installation "recipe" lives in another.
- **Automatic launchd:** Homebrew generates, installs, and manages the `.plist` file for you.
- **UV-native:** Scripts declare their Python requirement and deps in the script header.

---

## The "Monorepo + Tap" Architecture

Two separate Git repositories—ideal for many personal scripts without one repo per script.

1. **The Monorepo** (e.g., `personal-scripts`): Contains all scripts and their files, organized in subdirectories. The entire repo is versioned with Git tags (e.g., `v1.0.0`).
2. **The Tap Repo** (e.g., `homebrew-personal-services`): Your personal Homebrew channel. It contains a separate recipe (Ruby formula) for each script in your monorepo.
  
---

## Part 1: The Payload Monorepo

This is your main project. All your scripts live here, cleanly separated.

**Monorepo Directory Structure**
```
personal-scripts/
│
├── kube-backup/                  # Script 1
│   ├── bin/
│   │   └── kube-backup.py        # THE EXECUTABLE (UV shebang)
│   ├── etc/
│   │   └── config.ini.example    # DEFAULT CONFIG (user copies to config.ini)
│   └── lib/
│       └── support_files/
│           └── cluster_list.txt
│
├── log-rotator/                  # Script 2
│   ├── bin/
│   │   └── log-rotator.sh
│   └── etc/
 │       └── log-rotator.conf.example.example
│
└── README.md
```

### Example File Contents

`kube-backup/bin/kube-backup.py` — UV-native script with config defaulting to Homebrew etc and support files via env.

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pyyaml",
# ]
# ///

import os
import sys
import argparse
import configparser
from datetime import datetime
from pathlib import Path

# Homebrew wrapper will set this to opt_pkgshare.
SUPPORT_DIR_PATH = os.environ.get("KUBE_BACKUP_HOME")

def log(message):
    print(f"{datetime.now():%Y-%m-%d %H:%M:%S} - {message}", flush=True)

def default_config_path():
    # Default to Homebrew etc unless overridden
    prefix = os.environ.get("HOMEBREW_PREFIX") or "/opt/homebrew"
    return f"{prefix}/etc/kube-backup/config.ini"

def main():
    parser = argparse.ArgumentParser(description="Kube Backup Script")
    parser.add_argument("--config", default=default_config_path(),
                        help="Path to config file (default: Homebrew etc/kube-backup/config.ini)")
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    args = parser.parse_args()

    if args.version:
        print("kube-backup 1.0.0")
        sys.exit(0)

    log("Backup service started.")

    config = configparser.ConfigParser()
    try:
        read = config.read(args.config)
        if not read:
            print(f"ERROR: Config not found at {args.config}", file=sys.stderr, flush=True)
            sys.exit(1)
        backup_path = config.get('Settings', 'BackupPath')
        log(f"Using backup path: {backup_path}")
    except Exception as e:
        print(f"ERROR: Could not read config at {args.config}: {e}", file=sys.stderr, flush=True)
        sys.exit(1)

    if not SUPPORT_DIR_PATH:
        print("ERROR: KUBE_BACKUP_HOME not set (expected via brew wrapper).", file=sys.stderr, flush=True)
        sys.exit(1)

    support_file = Path(SUPPORT_DIR_PATH) / "lib" / "support_files" / "cluster_list.txt"
    try:
        clusters = support_file.read_text().splitlines()
        log(f"Found support file. Processing {len(clusters)} clusters...")
    except Exception as e:
        log(f"ERROR: Could not read support file at {support_file}: {e}")
        sys.exit(1)

    # ... (backup logic would go here) ...
    log("Backup complete.")

if __name__ == "__main__":
    main()
```

`kube-backup/etc/config.ini.example`

```ini
[Settings]
BackupPath = /Users/your-username/Backups/kube
# Add other settings here
```

---

## Part 2: The Tap Repo

This repo (e.g., a public GitHub repo named `homebrew-personal-services`) holds the recipes.

**Directory Structure**
```
homebrew-personal-services/
│
└── Formula/
    ├── kube-backup.rb        # Recipe for Script 1
    └── log-rotator.rb        # Recipe for Script 2
```

### Formula: `Formula/kube-backup.rb` (UV-first, modern service DSL)

```ruby
class KubeBackup < Formula
  desc "Back up Kubernetes configs (UV-powered Python script)"
  homepage "https://github.com/<your-username>/personal-scripts"
  url "https://github.com/<your-username>/personal-scripts/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "<fill-me>"
  license "MIT"

  depends_on "uv"  # UV runs the script; no Homebrew Python/venv needed.

  def install
    cd "kube-backup" do
      # Install the real script and make sure it's executable
      libexec.install "bin"
      chmod 0755, libexec/"bin/kube-backup.py"

      # Wrapper sets env and delegates to the real script (with UV shebang)
      (bin/"kube-backup").write_env_script libexec/"bin/kube-backup.py",
        KUBE_BACKUP_HOME: opt_pkgshare,
         HOMEBREW_PREFIX: HOMEBREW_PREFIX.to_s, # for default config discovery
        PYTHONUNBUFFERED: "1"

      # Install shared data for the script
      (pkgshare/"lib/support_files").install Dir["lib/support_files/*"]

      # Install example config; user copies to config.ini
      (etc/"kube-backup").install "etc/config.ini.example"
    end
  end

  service do
    run [opt_bin/"kube-backup", "--config", etc/"kube-backup/config.ini"]
    run_at_load true
    keep_alive false
    run_type :interval
    interval 3600
    environment_variables PATH: std_service_path_env
    working_dir var
    log_path var/"log/kube-backup.log"
    error_log_path var/"log/kube-backup.log"
  end

  def caveats
    <<~EOS
      A sample config was installed to:
        #{etc}/kube-backup/config.ini.example

      Copy it to activate and then edit:
        cp #{etc}/kube-backup/config.ini.example #{etc}/kube-backup/config.ini
        chmod 600 #{etc}/kube-backup/config.ini

      Start the service:
        brew services start kube-backup

      Logs:
        tail -f #{var}/log/kube-backup.log
    EOS
  end

  test do
    # Avoid running real backup logic; just validate CLI responds
     assert_match "Kube Backup Script", shell_output("#{bin}/kube-backup --help")
  end
end
```

**Notes**
- We depend only on `uv`. The script’s shebang `#!/usr/bin/env -S uv run --script` ensures the right interpreter and ephemeral environment per script header.
- The wrapper sets `KUBE_BACKUP_HOME` → `opt_pkgshare` and provides `HOMEBREW_PREFIX` so the script can default its config path cleanly.
- Data lives in `pkgshare`, configs in `etc`, logs in `var/log`, and we use the modern `service do` DSL.

---

## Part 3: The End-to-End Workflow

### A. First-Time Setup

**Create the Formula (quickly, after tagging the monorepo):**

```bash
brew create --tap=<your-username>/personal-services \
  https://github.com/<your-username>/personal-scripts/archive/refs/tags/v1.0.0.tar.gz \
  --set-name kube-backup
```

This command automatically:

1. Creates the `homebrew-personal-services` tap locally.
2. Creates the `kube-backup.rb` formula file.
3. Fills in the url and sha256.
4. Opens the file in your editor.

**Edit the Formula**

Paste the logic from the template above (especially the `cd "kube-backup" do` block) into the file and save it.

**Push Your Tap:**

```bash
cd "$(brew --repository <your-username>/personal-services)"
git add .
git commit -m "Add kube-backup formula"
# Create the 'homebrew-personal-services' repo on GitHub and push to it.
git remote add origin <git@github.com:<your-username>/homebrew-personal-services.git>
git push -u origin main
```

### B. Daily Management (The Payoff)

#### 1. Install Your Service

```bash
# Tap your channel (only needed once)
brew tap <your-username>/personal-services

# Install your script like any other tool
brew install kube-backup
```

#### 2. Set Up Your Config

`brew install` put the example config in `etc`. Copy it to create your active config.

```bash
# Get the Homebrew prefix path (e.g., /opt/homebrew)
PREFIX=$(brew --prefix)

# Copy the example config to the active config
cp "$PREFIX/etc/kube-backup/config.ini.example" "$PREFIX/etc/kube-backup/config.ini"

# Now, edit your personal config
nano "$PREFIX/etc/kube-backup/config.ini"
```

#### 3. Run Your Service

```bash
# This creates the .plist in ~/Library/LaunchAgents and loads it
brew services start kube-backup
```

---

## C. The Full Lifecycle
- Check Status: `brew services list`
- Stop Service: `brew services stop kube-backup`
- Restart Service: `brew services restart kube-backup`
- View Logs: `tail -f $(brew --prefix)/var/log/kube-backup.log`
- Uninstall: `brew services stop kube-backup && brew uninstall kube-backup`
- Upgrade Your Script:
  1. Push a `v1.0.1` tag to your `personal-scripts` repo.
  2. Update your `kube-backup.rb` formula file (and `log-rotator.rb`, etc.) to point to the new `v1.0.1` tarball.
  3. Run `brew upgrade`.
  4. Run `brew services restart kube-backup`. Your config in `etc` is safe.

---

## Extras & Gotchas
- **PATH in launchd**: We set `PATH: std_service_path_env` so `uv` is found reliably under Homebrew.
- **No venvs**: UV handles Python interpreter and dependencies on demand via the script header.
- **Defaults**: `--config` is optional and defaults to `$(brew --prefix)/etc/kube-backup/config.ini`, which works for both services and manual runs.
- **Apple Silicon vs Intel**: Homebrew prefix is `/opt/homebrew` on Apple Silicon and `/usr/local` on Intel; the formula passes `HOMEBREW_PREFIX` to the script so defaults are correct.
- **Log rotation**: `brew services` does not rotate logs; consider `newsyslog`, internal rotation, or periodic pruning.
