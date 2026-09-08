"""Synthetic consumer regression tests; these are not visual asset approvals."""
import copy
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import assemble_runtime as a


def write_json(path, value):
    path.write_text(json.dumps(value))


def triangle():
    blob = struct.pack('<9f', 0, 0, 0, 1, 0, 0, 0, 1, 0)
    doc = {'asset': {'version': '2.0'}, 'scene': 0, 'scenes': [{'nodes': [0]}],
           'nodes': [{'name': 'synthetic-triangle', 'mesh': 0}], 'meshes': [{'primitives': [{'attributes': {'POSITION': 0}}]}],
           'buffers': [{'byteLength': len(blob)}], 'bufferViews': [{'buffer': 0, 'byteLength': len(blob)}],
           'accessors': [{'bufferView': 0, 'componentType': 5126, 'count': 3, 'type': 'VEC3'}]}
    data = json.dumps(doc).encode()
    data += b' ' * (-len(data) % 4)
    return struct.pack('<4sII', b'glTF', 2, 28 + len(data) + len(blob)) + struct.pack('<II', len(data), 0x4e4f534a) + data + struct.pack('<II', len(blob), 0x004e4942) + blob


class AssemblyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.assets = self.root / 'assets'
        self.assets.mkdir()
        self.pointer = self.assets / 'photoreal-registry.json'
        self.pointer.write_text('last working release')
        self.runtime = b'{"synthetic": "runtime-test-not-production"}'
        self.bundle = self.fixture('synthetic-a')
        self.plan = self.root / 'plan.json'
        write_json(self.plan, {'schema': 1, 'entries': [{'bundle': str(self.bundle), 'artifact': 'glb'}]})

    def fixture(self, name):
        root = self.root / name
        root.mkdir()
        candidate = {'schema': 1, 'id': name, 'author': 'synthetic-author', 'source_ids': ['synthetic-source'],
                     'runtime_entry': {'id': name, 'artifact': 'glb', 'family': 'synthetic'}, 'artifacts': {}, 'context': {}}
        for kind, records in [('artifacts', {'glb': triangle()}), ('context', {'target': b'synthetic target', 'runtime': self.runtime, 'camera': b'synthetic camera', 'replay': b'synthetic replay'})]:
            for key, data in records.items():
                filename = key + ('.glb' if key == 'glb' else '.json')
                (root / filename).write_bytes(data)
                candidate[kind][key] = {'path': filename, 'sha256': a.digest(data)}
        contract = {'schema': 1, 'required_artifacts': ['glb'], 'required_context': ['target', 'runtime', 'camera', 'replay'],
                    'technical_checks': ['load'], 'visual_checks': ['target-match']}
        write_json(root / 'manifest.json', candidate)
        write_json(root / 'contract.json', contract)
        (root / 'proof.txt').write_text('SYNTHETIC mechanical acceptance fixture. No actual artistic approval.')
        for kind, check in [('technical', 'load'), ('visual', 'target-match')]:
            report = {'schema': 1, 'candidate_sha256': a.digest((root / 'manifest.json').read_bytes()),
                      'contract_sha256': a.digest((root / 'contract.json').read_bytes()),
                      'reviewer': 'synthetic-independent', 'inspected': True, 'verdict': 'pass', 'blockers': [],
                      'evidence': {'proof': {'path': 'proof.txt', 'sha256': a.digest((root / 'proof.txt').read_bytes())}},
                      'checks': {check: {'status': 'pass', 'reason': 'synthetic test assertion', 'evidence': ['proof']}}}
            write_json(root / f'{kind}.json', report)
        output = self.root / (name + '-bundle')
        a.gate(root / 'manifest.json', root / 'contract.json', root / 'technical.json', root / 'visual.json', profile='production', output=output)
        return output

    def assemble(self, **options):
        return a.assemble(plan=self.plan, assets=self.assets, runtime=self.runtime, **options)

    def reject_preserving_release(self):
        with self.assertRaises((a.GateError, OSError, ValueError, TypeError, KeyError)):
            self.assemble()
        self.assertEqual(self.pointer.read_text(), 'last working release')
        self.assertFalse(list(self.assets.glob('releases/.assembling-*')))

    def test_two_independent_bundles_published_and_revalidated(self):
        other = self.fixture('synthetic-b')
        write_json(self.plan, {'schema': 1, 'entries': [{'bundle': str(self.bundle)}, {'bundle': str(other)}]})
        result = self.assemble()
        self.assertEqual(result['models'], 2)
        registry = json.loads(self.pointer.read_bytes())
        self.assertEqual(registry['profile'], 'production')
        for entry in registry['entries']:
            self.assertEqual(a.digest((self.assets / entry['path']).read_bytes()), entry['sha256'])
            bundle = self.assets / entry['bundle']
            checked = a.gate(bundle / 'candidate/manifest.json', bundle / 'contract.json', bundle / 'reviews/technical/report.json', bundle / 'reviews/visual/report.json', profile='production')
            self.assertEqual(checked, json.loads((bundle / 'acceptance.json').read_bytes()))

    def test_missing_plan_fails_before_mutation(self):
        with self.assertRaises(a.GateError):
            a.assemble(assets=self.assets)
        self.assertEqual(self.pointer.read_text(), 'last working release')

    def test_actual_cli_defaults_production_and_rejects_legacy(self):
        result = subprocess.run([sys.executable, str(Path(a.__file__)), '--assets', str(self.assets)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('requires --plan', result.stderr)
        self.assertEqual(self.pointer.read_text(), 'last working release')

    def test_include_rendering_cannot_bypass_production(self):
        with self.assertRaises(a.GateError):
            self.assemble(include_rendering=True)
        self.assertEqual(self.pointer.read_text(), 'last working release')

    def test_missing_visual(self):
        (self.bundle / 'reviews/visual/report.json').unlink()
        self.reject_preserving_release()

    def test_failed_review(self):
        path = self.bundle / 'reviews/visual/report.json'
        doc = json.loads(path.read_bytes()); doc['verdict'] = 'fail'; write_json(path, doc)
        self.reject_preserving_release()

    def test_stale_artifact(self):
        (self.bundle / 'candidate/glb.glb').write_bytes(b'changed')
        self.reject_preserving_release()

    def test_stale_evidence(self):
        (self.bundle / 'reviews/visual/proof.txt').write_bytes(b'changed')
        self.reject_preserving_release()

    def test_stale_context(self):
        (self.bundle / 'candidate/camera.json').write_bytes(b'changed')
        self.reject_preserving_release()

    def test_current_runtime_differs_from_review(self):
        self.runtime = b'new runtime implementation'
        self.reject_preserving_release()

    def test_forged_acceptance_record(self):
        path = self.bundle / 'acceptance.json'
        doc = json.loads(path.read_bytes()); doc['profile'] = 'prototype'; write_json(path, doc)
        self.reject_preserving_release()

    def test_duplicate_ids_no_partial_publication(self):
        write_json(self.plan, {'schema': 1, 'entries': [{'bundle': str(self.bundle)}, {'bundle': str(self.bundle)}]})
        self.reject_preserving_release()

    def test_artifact_remap(self):
        write_json(self.plan, {'schema': 1, 'entries': [{'bundle': str(self.bundle), 'artifact': 'other'}]})
        self.reject_preserving_release()

    def test_explicit_empty_release_revokes_previous_entries(self):
        self.assemble()
        old = self.pointer.read_bytes()
        write_json(self.plan, {'schema': 1, 'entries': []})
        self.assemble()
        self.assertEqual(json.loads(self.pointer.read_bytes())['entries'], [])
        self.assertNotEqual(old, self.pointer.read_bytes())

    def test_publish_failure_leaves_previous_registry(self):
        with patch.object(a.os, 'replace', side_effect=OSError('synthetic interrupted pointer swap')):
            self.reject_preserving_release()

    def test_prototype_uses_separate_registry(self):
        with patch.object(a, 'prototype_entries', return_value=[]):
            self.assemble(profile='prototype')
        self.assertEqual(self.pointer.read_text(), 'last working release')
        self.assertEqual(json.loads((self.assets / 'photoreal-prototype-registry.json').read_bytes())['profile'], 'prototype')


if __name__ == '__main__':
    unittest.main()
