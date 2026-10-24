"""Railway and local entry point. The platform supplies PORT; one worker owns sockets."""
import os
import uvicorn
from .settings import validate_production


def main():
    validate_production(os.environ)
    port = int(os.getenv('PORT','8000'))
    if not 1 <= port <= 65535:
        raise ValueError('PORT must be between 1 and 65535')
    uvicorn.run('app.main:app', host='0.0.0.0', port=port, workers=1,
                ws_max_size=65536, ws_ping_interval=20, ws_ping_timeout=20,
                timeout_graceful_shutdown=10)


if __name__ == '__main__':
    main()
