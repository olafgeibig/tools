import sys
import logging
from pathlib import Path
from platformdirs import user_log_dir

def setup_logging():
    """Set up logging to user_log_dir"""
    log_dir = Path(user_log_dir("aiproxy"))
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "aiproxy.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("aiproxy")


logger = setup_logging()


def log(message):
    logger.info(message)


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
