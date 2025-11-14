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
│   ├── kube-backup.py            # Main script (UV shebang)
│   ├── config.yaml               # Default config (packaged with script)
│   └── support_files/            # Support files directory
│       └── cluster_list.txt
│
├── log-rotator/                  # Script 2
│   ├── log-rotator.sh
│   └── log-rotator.conf
│
└── README.md
```

### Script Implementation Requirements

Your script must implement the following pattern to work with the Homebrew wrapper:

**Environment Variables (injected by Homebrew wrapper):**
- `SCRIPT_HOME` - Path to support files directory (e.g., `/usr/local/share/kube-backup`)
- `SCRIPT_CONFIG` - Path to the packaged config file (e.g., `/usr/local/etc/kube-backup/config.yaml`)

**Required Script Features:**

1. **Config Path Resolution:**
   ```python
   def default_config_path():
       """Use SCRIPT_CONFIG from Homebrew or fallback to user config"""
       return os.environ.get("SCRIPT_CONFIG") or "~/.config/kube-backup/config.yaml"
   ```

2. **Config Directory Command:**
   ```python
   parser.add_argument("--config-dir", action="store_true", 
                      help="Output absolute path to config directory")
   
   if args.config_dir:
       config_path = args.config or default_config_path()
       config_dir = Path(config_path).parent.expanduser().resolve()
       print(config_dir)
       sys.exit(0)
   ```

3. **Support Files Access:**
   ```python
   support_dir = os.environ.get("SCRIPT_HOME")
   if not support_dir:
       print("ERROR: SCRIPT_HOME not set (expected via brew wrapper).", file=sys.stderr)
       sys.exit(1)
   
   support_file = Path(support_dir) / "support_files" / "cluster_list.txt"
   ```

4. **Config Loading with Clear Error Messages:**
   ```python
   def load_config(config_path):
       if not os.path.exists(config_path):
           print(f"ERROR: Configuration file not found: {config_path}", file=sys.stderr)
           print(f"Run: kube-backup --config-dir to find config location", file=sys.stderr)
           sys.exit(1)
       # ... load and validate config
   ```

**Packaged Config File:**
Include a default `config.yaml` in your script directory that gets installed by Homebrew. Users can edit this file directly after installation.

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
      libexec.install "kube-backup.py"
      chmod 0755, libexec/"kube-backup.py"

      # Wrapper sets env and delegates to the real script (with UV shebang)
      (bin/"kube-backup").write_env_script libexec/"kube-backup.py",
        SCRIPT_HOME: pkgshare,
        SCRIPT_CONFIG: etc/"kube-backup/config.yaml",
        PYTHONUNBUFFERED: "1"

      # Install support files for the script
      pkgshare.install Dir["support_files/*"]

      # Install default config file (user edits this directly)
      (etc/"kube-backup").install "config.yaml"
    end
  end

  service do
    run [opt_bin/"kube-backup", "--config", etc/"kube-backup/config.yaml"]
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
      Configuration file installed to:
        #{etc}/kube-backup/config.yaml

      Find config directory:
        kube-backup --config-dir

      Start the service:
        brew services start kube-backup

      Logs:
        tail -f #{var}/log/kube-backup.log
    EOS
  end
end
```

**Notes**
- We depend only on `uv`. The script's shebang `#!/usr/bin/env -S uv run --script` ensures the right interpreter and ephemeral environment per script header.
- The wrapper sets `SCRIPT_HOME` → `pkgshare` for support files and `SCRIPT_CONFIG` → `etc/script-name/config.yaml` for the configuration path.
- Data lives in `pkgshare`, configs in `etc`, logs in `var/log`, and we use the modern `service do` DSL.
- No `.example` files needed - the default config is packaged and edited directly by users.

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

Find the config directory and edit the packaged configuration:

```bash
kube-backup --config-dir
# Edit the config.yaml file in that directory
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
- **Defaults**: `--config` is optional and defaults to the path set by `SCRIPT_CONFIG` environment variable, or `~/.config/script-name/config.yaml` for manual runs.
- **Platform Independence**: The formula sets `SCRIPT_CONFIG` directly, so the script doesn't need to know about Homebrew prefixes or platform differences.
- **Security**: Config files contain API keys and secrets. Set secure permissions (`chmod 600`) on config files. Never commit secrets to version control.
- **Log rotation**: `brew services` does not rotate logs; consider `newsyslog`, internal rotation, or periodic pruning.
