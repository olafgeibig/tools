# AI Proxy

A profile-based proxy server for AI model APIs built on LiteLLM. This tool allows you to easily manage multiple proxy configurations for different environments (development, staging, production) with separate LiteLLM configurations.

## Features

- **Profile-based configuration** - Manage multiple proxy environments
- **Easy switching** between development, staging, and production setups
- **Environment variable management** - Secure API key handling
- **OpenTelemetry tracing** - Optional monitoring support
- **CLI interface** - Simple command-line profile management

## Installation

You can install `aiproxy` using `uv`:

```bash
uv tool install "git+https://github.com/olafgeibig/tools@main#subdirectory=aiproxy"
```

Verify the installation:

```bash
aiproxy --version
```

## First Run Configuration

On the first run, example configuration files are automatically copied to the canonical config directory of your operating system. You can run the following command to get the path to the config directory:

```bash
aiproxy --config-dir
```

This will show you where the configuration files are located. You should edit the copied files to match your needs, including:

- `config.yaml` - Main proxy configuration that defines a profile that points to `example.yaml` for the litellm configuration
- `example.yaml` - Example litellm configuration file

## Environment Variables

You can set environment variables to pass to the proxy server in the `env` section of `config.yaml`. For example API keys can be used in the litellm config: `os.environ/EXAMPLE_API_KEY` 

## Security

- Keep your `config.yaml` file secure (chmod 600) as it contains API keys
- Use environment variables for sensitive data when possible
- Consider using a secrets management system for production deployments
