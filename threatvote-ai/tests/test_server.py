import io
import json
from pathlib import Path

import pytest

import data
import server

SMALL_SETTINGS = {'n_trees': 10, 'boost_iters': 10}


@pytest.fixture(scope='module')
def result():
    return server.train(SMALL_SETTINGS)


def test_api_results_match_test_split_and_mistake_examples(result):
    json.dumps(result, allow_nan=False)
    dataset = result['dataset']
    assert dataset['synthetic']
    assert dataset['train_rows'] + dataset['test_rows'] == dataset['total']
    assert sum(dataset['families'].values()) == dataset['total']
    assert len(result['models']) == 4
    for model in result['models']:
        assert model['caught'] + model['missed'] == dataset['test_attacks']
        assert model['false_alarms'] + model['benign_correct'] == dataset['test_benign']
        assert sum(sum(row) for row in model['confusion']) == dataset['test_rows']
        for kind, metric in [('missed_attacks', 'missed'), ('false_alarms', 'false_alarms')]:
            mistakes = model['mistakes'][kind]
            assert mistakes['total'] == model[metric]
            assert sum(mistakes['by_family'].values()) == mistakes['total']
            assert len(mistakes['examples']) == min(mistakes['total'], 100)
            for example in mistakes['examples']:
                assert (example['Known label'] == data.BENIGN) == (kind == 'false_alarms')
                assert not set(data.IDENTIFIER_COLS) & set(example)


@pytest.mark.parametrize('values', [
    [], {'tree_depth': 0}, {'test_size': 1}, {'seed': -1}, {'n_trees': True},
    {'n_trees': 10.5}, {'learning_rate': float('nan')}, {'unknown': 1},
    {'source': 12}, {'max_rows': 100001},
])
def test_invalid_settings_are_rejected(values):
    with pytest.raises(ValueError):
        server.Settings.parse(values)


def test_dataset_paths_cannot_escape_raw_folder():
    with pytest.raises(ValueError):
        server.train({'source': '../requirements.txt'})


def test_cache_tracks_changes_in_dataset_file(tmp_path, monkeypatch):
    monkeypatch.setattr(data, 'RAW_DIR', tmp_path)
    path = tmp_path / 'traffic.csv'
    frame = data.generate_sample(n_rows=200)
    frame.to_csv(path, index=False)
    settings = {**SMALL_SETTINGS, 'source': path.name}
    first = server.train(settings)
    assert server.train(settings) is first
    extra = frame.iloc[[0]].copy()
    extra['Flow Duration'] += 1234567
    import pandas as pd
    pd.concat([frame, extra]).to_csv(path, index=False)
    second = server.train(settings)
    assert second['dataset']['total'] == first['dataset']['total'] + 1


class FakeSocket:
    def __init__(self, request):
        self.request = io.BytesIO(request)
        self.response = bytearray()

    def makefile(self, *args, **kwargs):
        return self.request

    def sendall(self, content):
        self.response.extend(content)


def request(method, path, payload=None):
    body = json.dumps(payload).encode() if payload is not None else b''
    headers = f'{method} {path} HTTP/1.0\r\nHost: localhost\r\nContent-Length: {len(body)}\r\n\r\n'.encode()
    socket = FakeSocket(headers + body)
    server.Handler(socket, ('127.0.0.1', 0), None)
    header, body = bytes(socket.response).split(b'\r\n\r\n', 1)
    return int(header.split()[1]), body


def test_http_training_and_errors(result):
    status, body = request('POST', '/api/train', SMALL_SETTINGS)
    assert status == 200
    assert json.loads(body) == result
    status, body = request('POST', '/api/train', {'source': '../../README.md'})
    assert status == 400
    assert 'error' in json.loads(body)
    assert request('POST', '/api/missing', {})[0] == 404
    status, body = request('GET', '/api/datasets')
    assert status == 200
    assert json.loads(body)['sources'][0]['id'] == 'sample'


def test_http_serves_frontend_and_animated_asset_without_exposing_source(tmp_path, monkeypatch):
    monkeypatch.setattr(server, 'DIST', tmp_path)
    (tmp_path / 'index.html').write_text('<title>ThreatVote AI</title>')
    assert request('GET', '/')[1] == b'<title>ThreatVote AI</title>'
    assert request('GET', '/../../requirements.txt')[0] == 404
    assert request('GET', '/%2e%2e/requirements.txt')[0] == 404
    status, body = request('GET', '/mascot/monster-talking.gif')
    assert status == 200
    assert body[:6] in (b'GIF87a', b'GIF89a')
