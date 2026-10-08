"""Local Python API and static host for ThreatVote AI's custom frontend.

Build the frontend once, then run: python server.py
For Vite development, run: python server.py --api-only
"""

import argparse
from dataclasses import asdict, dataclass
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import mimetypes
from pathlib import Path
import threading
from urllib.parse import unquote, urlsplit

import data
import models

ROOT = Path(__file__).resolve().parent
DIST = ROOT / 'frontend' / 'dist'
TRAIN_LOCK = threading.Lock()
MASCOT_FILES = {
    '/mascot/monster-talking.gif': ROOT / 'monster-talking.gif',
    '/mascot/monster-still.png': ROOT / 'monster-talking-still.png',
}


@dataclass(frozen=True)
class Settings:
    source: str = 'sample'
    max_rows: int = 20000
    test_size: float = 0.25
    seed: int = 42
    tree_depth: int = 8
    n_trees: int = 100
    boost_iters: int = 100
    learning_rate: float = 0.5

    @classmethod
    def parse(cls, values):
        if not isinstance(values, dict):
            raise ValueError('Training settings must be a JSON object.')
        defaults = asdict(cls())
        if set(values) - set(defaults):
            raise ValueError('Unknown training setting.')
        defaults.update(values)
        bounds = {
            'max_rows': (2000, 100000), 'test_size': (0.1, 0.4),
            'seed': (0, 2**32 - 1), 'tree_depth': (2, 20),
            'n_trees': (10, 300), 'boost_iters': (10, 300), 'learning_rate': (0.01, 2),
        }
        for key, (lower, upper) in bounds.items():
            value = defaults[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f'{key} must be a finite number.')
            if key not in ('test_size', 'learning_rate') and not isinstance(value, int):
                raise ValueError(f'{key} must be a whole number.')
            if not lower <= value <= upper:
                raise ValueError(f'{key} must be between {lower} and {upper}.')
        if not isinstance(defaults['source'], str):
            raise ValueError('Choose a valid data source.')
        return cls(**defaults)


def sources():
    return [{'id': 'sample', 'name': 'Demo traffic (synthetic)', 'synthetic': True}] + [
        {'id': path.name, 'name': path.name, 'synthetic': False}
        for path in data.list_raw_files()
    ]


def source_path(source):
    if source == 'sample':
        if not data.SAMPLE_PATH.exists():
            data.load_sample()
        return data.SAMPLE_PATH
    # Only allow files discovered in data/raw, not caller-supplied paths.
    available = {path.name: path for path in data.list_raw_files()}
    if source not in available:
        raise ValueError('Data source not found. Choose the demo or a CSV in data/raw/.')
    return available[source]


def records(frame):
    return json.loads(frame.to_json(orient='records'))


@lru_cache(maxsize=4)
def _train(settings, file_version):
    path = source_path(settings.source)
    frame = data.load_sample() if settings.source == 'sample' else data.load_raw(
        path, max_rows=settings.max_rows, seed=settings.seed)
    target = (frame[data.LABEL_COL] != data.BENIGN).astype(int)
    if target.nunique() != 2:
        raise ValueError('Choose a dataset containing both benign traffic and attacks.')
    try:
        X_train, X_test, y_train, y_test, _, families = data.split(
            frame, test_size=settings.test_size, seed=settings.seed)
    except ValueError as exc:
        raise ValueError('This dataset cannot be split with these settings. Try a larger sample or test set.') from exc
    if y_train.nunique() != 2 or y_test.nunique() != 2:
        raise ValueError('Both training and test sets need benign traffic and attacks. Try a larger sample.')
    built = models.build_models(tree_depth=settings.tree_depth, n_trees=settings.n_trees,
                                boost_iters=settings.boost_iters,
                                learning_rate=settings.learning_rate, seed=settings.seed)
    results = models.train_and_evaluate(built, X_train, y_train, X_test, y_test)
    output_models = []
    for name, result in results.items():
        tn, fp, fn, tp = (int(v) for v in result['confusion'].ravel())
        outcomes = models.outcome_labels(y_test, result['y_pred'])
        mistakes = {}
        for kind, outcome in [('false_alarms', 'False Positive'), ('missed_attacks', 'False Negative')]:
            mask = outcomes == outcome
            examples = X_test.loc[mask].head(100).copy()
            examples.insert(0, 'Known label', families.loc[examples.index])
            examples.insert(0, 'Connection', [int(index) for index in examples.index])
            mistakes[kind] = {
                'total': int(mask.sum()),
                'examples': records(examples),
                'by_family': {str(k): int(v) for k, v in families.loc[mask].value_counts().items()},
            }
        output_models.append({
            'name': name, 'accuracy': float(result['accuracy']),
            'precision': float(result['precision']), 'recall': float(result['recall']),
            'f1': float(result['f1']), 'train_seconds': float(result['train_seconds']),
            'confusion': result['confusion'].tolist(),
            'caught': tp, 'missed': fn, 'false_alarms': fp, 'benign_correct': tn,
            'mistakes': mistakes,
        })
    return {
        'settings': asdict(settings),
        'dataset': {
            'source': settings.source, 'synthetic': settings.source == 'sample',
            'total': len(frame), 'benign': int((target == 0).sum()), 'attacks': int(target.sum()),
            'train_rows': len(X_train), 'test_rows': len(X_test),
            'test_attacks': int(y_test.sum()), 'test_benign': int((y_test == 0).sum()),
            'families': {str(k): int(v) for k, v in frame[data.LABEL_COL].value_counts().items()},
            'sample': records(frame.head(20)),
        },
        'models': output_models,
    }


def train(values):
    settings = Settings.parse(values)
    path = source_path(settings.source)
    stat = path.stat()
    with TRAIN_LOCK:
        return _train(settings, (stat.st_mtime_ns, stat.st_size))


class Handler(BaseHTTPRequestHandler):
    def send_bytes(self, status, body, content_type):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_json(self, status, payload):
        self.send_bytes(status, json.dumps(payload, allow_nan=False).encode(), 'application/json; charset=utf-8')

    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        if path == '/api/health':
            return self.send_json(200, {'status': 'ok'})
        if path == '/api/datasets':
            return self.send_json(200, {'sources': sources()})
        if path.startswith('/api/'):
            return self.send_json(404, {'error': 'API route not found.'})
        if path in MASCOT_FILES:
            asset = MASCOT_FILES[path]
        else:
            asset = (DIST / path.lstrip('/')).resolve()
            if not asset.is_relative_to(DIST.resolve()):
                return self.send_json(404, {'error': 'File not found.'})
            if path == '/':
                asset = DIST / 'index.html'
        if not asset.is_file():
            return self.send_json(404, {'error': 'File not found. Build the frontend with npm run build.'})
        content_type = mimetypes.guess_type(asset.name)[0] or 'application/octet-stream'
        self.send_bytes(200, asset.read_bytes(), content_type)

    def do_POST(self):
        if urlsplit(self.path).path != '/api/train':
            return self.send_json(404, {'error': 'API route not found.'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 4096:
                raise ValueError('Send a JSON settings object of at most 4096 bytes.')
            payload = json.loads(self.rfile.read(length))
            result = train(payload)
        except (ValueError, KeyError, UnicodeDecodeError) as exc:
            return self.send_json(400, {'error': str(exc)})
        except Exception:
            self.log_error('Model training failed.')
            return self.send_json(500, {'error': 'Training failed. Check your dataset and try again.'})
        self.send_json(200, result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--api-only', action='store_true', help='Run API before frontend build for Vite development.')
    args = parser.parse_args()
    if not args.api_only and not (DIST / 'index.html').exists():
        parser.error('Build the frontend first: cd frontend && npm install && npm run build')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    print(f'ThreatVote AI is ready at http://localhost:{args.port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopping ThreatVote AI.', flush=True)
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
