""" Main Publ application """


import logging
import logging.handlers
import os
import signal
from urllib.parse import urlparse

import flask
import publ
from flask_hookserver import Hooks

logging.basicConfig(level=logging.INFO)

LOGGER = logging.getLogger(__name__)
LOGGER.info("Setting up")


APP_PATH = os.path.dirname(os.path.abspath(__file__))

config = {
    # The database connection configuration. This is a list of parameters
    # passed to PonyORM's db.bind() method; see
    # https://docs.ponyorm.com/firststeps.html#database-binding
    # for more information.
    #
    # NOTE: If this involves credentials (e.g. mysql, postgres, etc.) you
    # should put this into an appropriate environment variable in a file that
    # doesn't get checked in.
    'database_config': {
        'provider': 'sqlite',
        'filename': os.path.join(APP_PATH, 'index.db')
    },

    # How many image rendering threads to use
    'image_render_threads': 2,

    # The timezone for the site
    # 'timezone': tz.tzlocal(),      # default; based on the server
    'timezone': 'US/Pacific',      # by name

    # Caching configuration; see https://pythonhosted.org/Flask-Cache for
    # more information
    'cache': {
        'CACHE_TYPE': 'memcached',
        'CACHE_DEFAULT_TIMEOUT': 3659,
        'CACHE_THRESHOLD': 500,
        'CACHE_KEY_PREFIX': 'plaidweb.site',
    } if not os.environ.get('FLASK_DEBUG') else {
        'CACHE_NO_NULL_WARNING': True
    },
}

# Create the application instance
app = publ.Publ(__name__, config)

# Configure the GitHub publishing webhook
app.config['GITHUB_WEBHOOKS_KEY'] = os.environ.get('GITHUB_SECRET')
app.config['VALIDATE_IP'] = False

@app.path_alias_regex(r'/\.well-known/(host-meta|webfinger).*')
def redirect_bridgy(match):
    """ support ActivityPub via fed.brid.gy """
    return 'https://fed.brid.gy' + flask.request.full_path, False

# Deployment hook for self-hosted instance
hooks = Hooks(app, url='/_gh')


@hooks.hook('push')
def deploy(data, delivery):
    import threading
    import subprocess
    import flask

    try:
        result = subprocess.check_output(
            ['./deploy.sh', 'nokill'],
            stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as err:
        LOGGER.error("Deployment failed: %s", err.output)
        return flask.Response(err.output, status_code=500, mimetype='text/plain')

    def restart_server(pid):
        LOGGER.info("Restarting")
        os.kill(pid, signal.SIGHUP)

    LOGGER.info("Restarting server in 3 seconds...")
    threading.Timer(3, restart_server, args=[os.getpid()]).start()

    return flask.Response(result, mimetype='text/plain')
