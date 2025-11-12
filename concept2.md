# Concept: Managing Personal Scripts as Services with Homebrew

This document outlines a professional architecture for managing a personal executable (like your `kube-backup` Python script) as a launchd LaunchAgent, fully managed by Homebrew.

This concept treats your personal script just like any other formula (nginx, postgresql, etc.), giving you:

- A Single Command: `brew services start kube-backup`
- Version Control: `brew upgrade kube-backup`
- Clean Separation: Your script's code lives in one repo, and its installation "recipe" lives in another.
- Automatic launchd: Homebrew generates, installs, and manages the .plist file for you.

## The "Monorepo + Tap" Architecture

This professional model uses two separate Git repositories. It is an ideal way to manage multiple personal scripts without creating a separate repository for each one.

1. The Monorepo (e.g., personal-scripts): This single repo contains all your scripts and their files, organized in sub-directories. The entire repo is versioned with Git tags (e.g., v1.0.0).
2. The Tap Repo (e.g., homebrew-personal-services): This is your personal Homebrew "channel." It contains a separate "recipe" (Ruby formula) for each script in your monorepo.

## Part 1: The Payload Monorepo

This is your main project. All your scripts live here, cleanly separated.

Monorepo Directory Structure
```
personal-scripts/
│
├── kube-backup/                  # Script 1
│   ├── bin/
│   │   └── kube-backup.py        # 1. THE EXECUTABLE
│   ├── etc/
│   │   └── config.ini.default    # 2. THE DEFAULT CONFIG FILE
│   └── lib/
│       └── support_files/        # 4. THE SUPPORT FILES
│           └── cluster_list.txt
│
├── log-rotator/                  # Script 2
│   ├── bin/
│   │   └── log-rotator.sh
│   └── etc/
│       └── log-rotator.conf
│
└── README.md
```

### Example File Contents

`kube-backup/bin/kube-backup.py`

A sample Python script that reads its config, finds its support files (using an environment variable), and logs to the console.

```
#!/usr/bin/env python3
import os
import sys
import argparse
import configparser
from datetime import datetime

# This is the key: The Homebrew formula will set this env var
# to point to the installation's 'libexec' directory.
SUPPORT_DIR_PATH = os.environ.get("KUBE_BACKUP_HOME")

def log(message):
    """Logs to stdout, which brew services will capture."""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp} - {message}")

def main():
    parser = argparse.ArgumentParser(description="Kube Backup Script")
    parser.add_argument("--config", required=True, help="Path to config file")
    args = parser.parse_args()

    log("Backup service started.")

    # 1. Read the Config File
    config = configparser.ConfigParser()
    try:
        config.read(args.config)
        backup_path = config.get('Settings', 'BackupPath')
        log(f"Using backup path: {backup_path}")
    except Exception as e:
        print(f"ERROR: Could not read config at {args.config}: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Find and Use Support Files
    if not SUPPORT_DIR_PATH:
        log("ERROR: KUBE_BACKUP_HOME env var not set.")
        sys.exit(1)

    support_file = os.path.join(SUPPORT_DIR_PATH, "lib/support_files/cluster_list.txt")
    try:
        with open(support_file, 'r') as f:
            clusters = f.read().splitlines()
        log(f"Found support file. Processing {len(clusters)} clusters...")
    except Exception as e:
        log(f"ERROR: Could not read support file at {support_file}: {e}")
        sys.exit(1)

    # ... (backup logic would go here) ...
    log("Backup complete.")

if __name__ == "__main__":
    main()
```

`kube-backup/etc/config.ini.default`

Your script's default configuration.

```
[Settings]
BackupPath = /Users/your-username/Backups/kube
# Add other settings here
```

## Part 2: The Tap Repo

This repo (e.g., a public GitHub repo named homebrew-personal-services) holds the "recipes."

Directory Structure

```
homebrew-personal-services/
│
└── Formula/
    ├── kube-backup.rb        # Recipe for Script 1
    └── log-rotator.rb        # Recipe for Script 2
```

The Formula: `Formula/kube-backup.rb`

This is the "concept" file. It's a Ruby class that tells Homebrew how to handle the kube-backup script.

```
class KubeBackup < Formula
  desc "A script to back up Kubernetes configs"
  homepage "[https://github.com/](https://github.com/)<your-username>/personal-scripts"
  
  # The URL to your v1.0.0 release tarball *of the entire monorepo*
  url "[https://github.com/](https://github.com/)<your-username>/personal-scripts/archive/refs/tags/v1.0.0.tar.gz"
  # You get this by running: shasum -a 256 v1.0.0.tar.gz
  sha256 "abc123def456..." 
  
  # This version applies to the entire monorepo
  version "1.0.0"

  # Define dependencies, e.g., Python
  depends_on "python3"

  #
  # === INSTALL: Handling All File Types from a Monorepo ===
  # This block runs when the user types 'brew install'
  #
  def install
    # Homebrew unpacks the *entire* 'personal-scripts' tarball.
    # The current working directory is the root of that unpacked repo.
    # We **change directory** into the specific script's folder.
    cd "kube-backup" do
      #
      # --- From this point, the logic is identical to the single-repo model ---
      #
      
      # 1. EXECUTABLE & 4. SUPPORT FILES
      # Install *all* files from this subdir (bin/, lib/) into 'libexec'.
      # 'libexec' is the standard place for a formula's internal files.
      libexec.install Dir["*"]

      # 2. CREATE A WRAPPER SCRIPT
      # This creates a smart script at "$(brew --prefix)/bin/kube-backup"
      # This script automatically sets the KUBE_BACKUP_HOME env var
      # and then calls the *real* script inside 'libexec'.
      (bin/"kube-backup").write_env_script libexec/"bin/kube-backup.py", 
        KUBE_BACKUP_HOME: libexec

      # 3. CONFIG FILE
      # Install the default config file into 'etc'
      # Homebrew *never* overwrites user changes in 'etc' on upgrade.
      (etc/"kube-backup").install "etc/config.ini.default"
    end
  end

  #
  # === SERVICE: Handling the launchd Service ===
  # This block is *unchanged*. It runs when the user types 'brew services start'
  #
  def service
    {
      # This generates a user-level LaunchAgent.
      # It does NOT require 'sudo'.
      run: [
        opt_bin/"kube-backup",  # The wrapper script in 'bin'
        "--config", etc/"kube-backup/config.ini" # Points to the *user's* config
      ],
      run_at_load: true,
      start_interval: 3600, # Run every hour (3600 seconds)

      # 3. LOG FILES
      # This redirects all console output (stdout/stderr)
      # to a log file managed by Homebrew.
      log_path: var/"log/kube-backup.log",
      error_log_path: var/"log/kube-backup.log"
    }
  end

  test do
    # A simple test to verify installation
    system "#{bin}/kube-backup", "--help"
  end
end
```

## Part 3: The End-to-End Workflow

Here is how you would use this new, professional setup.

### A. First-Time Setup

#### Create the Formula (The Easy Way):

Once your personal-scripts repo has a v1.0.0 tag, run this on your Mac:

```
# Replace with your username and repo names
brew create --tap=<your-username>/personal-services \
[https://github.com/](https://github.com/)<your-username>/personal-scripts/archive/refs/tags/v1.0.0.tar.gz \
--set-name kube-backup
```

This command automatically: 

1. Creates the `homebrew-personal-services` tap locally.
2. Creates the `kube-backup.rb` formula file.
3. Fills in the url and sha256.
4. Opens the file in your editor.

#### Edit the Formula

Copy/paste the logic from the `kube-backup.rb` template above (especially the cd "kube-backup" do block) into the new file and save it.

#### Push Your Tap:

```
cd $(brew --repository <your-username>/personal-services)
git add .
git commit -m "Add kube-backup formula"
# Now create the 'homebrew-personal-services' repo on GitHub
# and push to it.
git remote add origin ...
git push -u origin main
```

### B. Daily Management (The Payoff)

#### 1. Install Your Service

```
# Tap your channel (only need to do this once)
brew tap <your-username>/personal-services

# Install your script like any other tool
brew install kube-backup
```

#### 2. Set Up Your Config

`brew install` put the default config in etc. You must copy it to create your user config.

```
# Get the Homebrew prefix path (e.g., /opt/homebrew)
PREFIX=$(brew --prefix)

# Copy the default config to the active config
cp $PREFIX/etc/kube-backup/config.ini.default $PREFIX/etc/kube-backup/config.ini

# Now, edit your personal config
nano $PREFIX/etc/kube-backup/config.ini
```

#### 3. Run Your Service
```
# This creates the .plist in ~/Library/LaunchAgents and loads it
brew services start kube-backup
```

## C. The Full Lifecycle
- Check Status: `brew services list`
- Stop Service: `brew services stop kube-backup`
- Restart Service: `brew services restart kube-backup`
- View Logs: `tail -f $(brew --prefix)/var/log/kube-backup.log`
- Upgrade Your Script:
  1. Push a v1.0.1 tag to your personal-scripts repo.
  2. Update your `kube-backup.rb` formula file (and `log-rotator.rb`, etc.) to point to the new v1.0.1 tarball.
  3. Run `brew upgrade`.
  4. Run `brew services restart kube-backup`. Your config in etc is safe.