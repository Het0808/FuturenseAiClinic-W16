import os
import functools

# 1. Evaluate environment configuration
# Tracing is enabled only if public and secret keys exist in system environment variables.
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

LANGFUSE_ENABLED = False

if LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY:
    try:
        # Try importing official Langfuse decorators
        from langfuse.decorators import observe, langfuse_context
        LANGFUSE_ENABLED = True
        print("[OBSERVABILITY] Langfuse telemetry logging initialized successfully.")
    except ImportError:
        print("[OBSERVABILITY WARNING] LANGFUSE keys found, but 'langfuse' package is not installed.")
        print("Run: pip install langfuse")

# 2. Fallback: No-Op telemetry wrappers
# If Langfuse is disabled, we expose identical signatures that act as a direct pass-through.
# This prevents importing components from crashing and saves developer time.
if not LANGFUSE_ENABLED:
    
    # Dummy decorator mimicking the signature of the real Langfuse decorator
    def observe(*args, **kwargs):
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*wargs, **wkwargs):
                # Simply calls the original function with its args and returns outputs
                return func(*wargs, **wkwargs)
            return wrapper
        return decorator

    # Dummy class containing standard context methods used to update active trace metrics
    class DummyContext:
        def update_current_observation(self, *args, **kwargs):
            # No-op: does nothing when telemetry is disabled
            pass
            
        def update_current_trace(self, *args, **kwargs):
            # No-op: does nothing when telemetry is disabled
            pass

    # Instantiate the dummy context
    langfuse_context = DummyContext()
    print("[OBSERVABILITY] No-Op Telemetry Fallback loaded (Tracing disabled).")
