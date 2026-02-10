#!/usr/bin/env python3
"""
HTTPS + Socket.IO server (Python replacement for server_secure.cjs).

Dependencies:
    pip install flask python-socketio eventlet

NOTE: The /proxy/* endpoint from the original Node.js server has been removed.
If proxy support is needed in the future, implement a Flask /proxy/<path:url>
route using the `requests` library to forward the request and return the response.
"""

import os
import argparse
import mimetypes

import eventlet
import eventlet.wsgi
import socketio
from flask import Flask, send_from_directory, make_response


# ── Custom MIME types (mirrors the original server_secure.cjs configuration) ──
_CUSTOM_MIME_TYPES = {
    '.czml':    'application/json',
    '.geojson': 'application/json',
    '.topojson': 'application/json',
    '.wasm':    'application/wasm',
    '.ktx2':    'image/ktx2',
    '.gltf':    'model/gltf+json',
    '.bgltf':   'model/gltf-binary',
    '.glb':     'model/gltf-binary',
    '.b3dm':    'application/octet-stream',
    '.pnts':    'application/octet-stream',
    '.i3dm':    'application/octet-stream',
    '.cmpt':    'application/octet-stream',
    '.geom':    'application/octet-stream',
    '.vctr':    'application/octet-stream',
    '.glsl':    'text/plain',
}
for _ext, _mime in _CUSTOM_MIME_TYPES.items():
    mimetypes.add_type(_mime, _ext)

# Extensions for which we check the first 3 bytes for a gzip magic header
GZIP_MAGIC   = b'\x1f\x8b\x08'
TILESET_EXTS = {'.b3dm', '.pnts', '.i3dm', '.cmpt', '.glb', '.geom', '.vctr'}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SSL_CERT   = os.path.join(SCRIPT_DIR, 'ssl', 'ca.crt')
SSL_KEY    = os.path.join(SCRIPT_DIR, 'ssl', 'ca.key')


# ── Socket.IO server ──────────────────────────────────────────────────────────
sio = socketio.Server(cors_allowed_origins='*', async_mode='eventlet')


@sio.event
def connect(sid, environ):
    print(f'socket connection established: {sid}')


@sio.event
def disconnect(sid):
    print(f'socket disconnected: {sid}')


@sio.on('*')
def catch_all(event, sid, data):
    """Re-broadcast every event to all connected clients (dumb relay)."""
    print(f'event={event}  data={data}')
    sio.emit(event, data)


# ── Flask app (static file server) ───────────────────────────────────────────
flask_app = Flask(__name__, static_folder=SCRIPT_DIR, static_url_path='')


@flask_app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = (
        'Origin, X-Requested-With, Content-Type, Accept'
    )
    return response


@flask_app.route('/', defaults={'path': 'index.html'})
@flask_app.route('/<path:path>')
def serve_static(path):
    full_path = os.path.join(SCRIPT_DIR, path)
    if not os.path.isfile(full_path):
        return make_response('Not found', 404)

    response = make_response(send_from_directory(SCRIPT_DIR, path))

    # Mirror the original gzip-detection for known 3D tileset formats
    _, ext = os.path.splitext(path)
    if ext.lower() in TILESET_EXTS:
        try:
            with open(full_path, 'rb') as f:
                if f.read(3) == GZIP_MAGIC:
                    response.headers['Content-Encoding'] = 'gzip'
        except OSError:
            pass

    return response


wsgi_app = socketio.WSGIApp(sio, flask_app)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='HTTPS + Socket.IO server.')
    ap.add_argument('--port',   type=int,          default=8080,
                    help='Port to listen on (default: 8080).')
    ap.add_argument('--public', action='store_true',
                    help='Listen on all interfaces (default: localhost only).')
    args = ap.parse_args()

    host  = '0.0.0.0' if args.public else 'localhost'
    scope = 'publicly' if args.public else 'locally'
    print(f'Dev server running {scope}.  Connect to https://localhost:{args.port}/')

    listener = eventlet.listen((host, args.port))
    ssl_listener = eventlet.wrap_ssl(
        listener,
        server_side=True,
        certfile=SSL_CERT,
        keyfile=SSL_KEY,
    )
    eventlet.wsgi.server(ssl_listener, wsgi_app)
