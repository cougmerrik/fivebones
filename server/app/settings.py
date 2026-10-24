"""Explicit public origins and production guards; never log database credentials."""
from urllib.parse import urlsplit


def origins(value):
    result = []
    for entry in value.split(','):
        entry = entry.strip().rstrip('/')
        if not entry:
            continue
        url = urlsplit(entry)
        if (url.scheme not in ('http','https') or not url.netloc or url.path or url.query
                or url.fragment or url.username or url.password or '*' in entry):
            raise ValueError('Allowed origins must be exact HTTP(S) origins, comma-separated')
        if entry not in result:
            result.append(entry)
    return result


def validate_production(env):
    if env.get('APP_ENV', 'development') != 'production':
        return
    if not env.get('DATABASE_URL','').startswith(('postgres://','postgresql://','postgresql+psycopg://')):
        raise ValueError('Production requires a PostgreSQL DATABASE_URL')
    if len(env.get('HOST_INVITE_SECRET','')) < 24:
        raise ValueError('Production requires HOST_INVITE_SECRET with at least 24 characters')
    app_url = urlsplit(env.get('APP_BASE_URL',''))
    if (app_url.scheme != 'https' or not app_url.netloc or app_url.username or app_url.password
            or app_url.path not in ('','/') or app_url.query or app_url.fragment):
        raise ValueError('Production requires an HTTPS APP_BASE_URL')
    for key in ('ALLOWED_ORIGINS','WS_ALLOWED_ORIGINS'):
        allowed = origins(env.get(key, env.get('ALLOWED_ORIGINS','') if key=='WS_ALLOWED_ORIGINS' else ''))
        if not allowed or any(not origin.startswith('https://') for origin in allowed):
            raise ValueError(f'Production requires explicit HTTPS {key}')
    if env.get('WEB_CONCURRENCY','1') != '1':
        raise ValueError('Use one API worker; WebSocket routing is process-local')
