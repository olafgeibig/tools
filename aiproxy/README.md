# AI Proxy

A profile-based proxy server for AI model APIs built on LiteLLM. This tool allows you to easily manage multiple proxy configurations for different environments (development, staging, production) with separate LiteLLM configurations.

## Features

- **Profile-based configuration** - Manage multiple proxy environments
- **Easy switching** between development, staging, and production setups
- **Environment variable management** - Secure API key handling
- **OpenTelemetry tracing** - Optional monitoring support
- **CLI interface** - Simple command-line profile management

## Installation

TODO brew install and service

aiproxy.py --help shows the options

## Environment Variables

You can set these environment variables to customize behavior:

- Any API keys defined in the `env` section of config.yaml

## Security

- Keep your `config.yaml` file secure (chmod 600) as it contains API keys
- Use environment variables for sensitive data when possible
- Consider using a secrets management system for production deployments

## Development

### Running in Development
Create a dev directory in the project and have a set of config files there that will be used by doing

```bash
# Use the development script
./run_dev.sh
```
