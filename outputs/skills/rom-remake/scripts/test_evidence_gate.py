"""Synthetic fixtures test mechanical rejection only, never artistic approval."""
import json
from pathlib import Path
import tempfile
import unittest

from evidence_gate import GateError, digest, gate


class EvidenceGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.candidate = self.root / 'candidate.json'
        self.contract = self.root / 'contract.json'
        self.technical = self.root / 'technical.json'
        self.visual = self.root / 'visual.json'
        self.doc = {'schema': 1, 'id': 'synthetic-test-not-art', 'author': 'test-builder',
                    'source_ids': ['synthetic-fixture'], 'artifacts': {}, 'context': {}}
        for kind, keys in [('artifacts', ['glb']), ('context', ['target', 'runtime', 'camera', 'replay'])]:
            for key in keys:
                name = key + '.txt'
                content = ('synthetic ' + key).encode()
                (self.root / name).write_bytes(content)
                self.doc[kind][key] = {'path': name, 'sha256': digest(content)}
        self.rules = {'schema': 1, 'required_artifacts': ['glb'],
                      'required_context': ['target', 'runtime', 'camera', 'replay'],
                      'technical_checks': ['loads'], 'visual_checks': ['matches-target']}
        self.write(self.candidate, self.doc)
        self.write(self.contract, self.rules)
        (self.root / 'proof.txt').write_text('synthetic review evidence')
        self.reports = {}
        for name, path, check in [('technical', self.technical, 'loads'), ('visual', self.visual, 'matches-target')]:
            self.reports[name] = {'schema': 1, 'candidate_sha256': digest(self.candidate.read_bytes()),
                                  'contract_sha256': digest(self.contract.read_bytes()),
                                  'reviewer': 'test-independent', 'inspected': True, 'verdict': 'pass',
                                  'blockers': [], 'evidence': {'proof': {'path': 'proof.txt',
                                  'sha256': digest((self.root / 'proof.txt').read_bytes())}},
                                  'checks': {check: {'status': 'pass', 'reason': 'synthetic fixture assertion',
                                                       'evidence': ['proof']}}}
            self.write(path, self.reports[name])

    def write(self, path, value):
        path.write_text(json.dumps(value))

    def run_gate(self, **options):
        args = dict(candidate=self.candidate, contract=self.contract, technical=self.technical,
                    visual=self.visual, profile='production')
        args.update(options)
        return gate(**args)

    def reject(self, **options):
        with self.assertRaises((GateError, OSError, ValueError)):
            self.run_gate(**options)

    def test_production_bundle_preserves_exact_bytes(self):
        destination = self.root / 'accepted'
        record = self.run_gate(output=destination)
        self.assertEqual(record['status'], 'production-evidence-accepted')
        self.assertFalse(record['artistic_quality_evaluated_by_checker'])
        for path, expected in record['files'].items():
            self.assertEqual(digest((destination / path).read_bytes()), expected)
        self.assertEqual((destination / 'candidate/manifest.json').read_bytes(), self.candidate.read_bytes())
        # Bundle is self-contained and can be checked again after original inputs are gone.
        self.temp2 = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp2.cleanup)
        import shutil
        moved = Path(self.temp2.name) / 'accepted'
        shutil.copytree(destination, moved)
        result = gate(moved / 'candidate/manifest.json', moved / 'contract.json',
                      moved / 'reviews/technical/report.json', moved / 'reviews/visual/report.json', profile='production')
        self.assertEqual(result, record)

    def test_prototype_without_visual_explicitly_labeled(self):
        self.assertEqual(self.run_gate(profile='prototype', visual=None)['status'], 'prototype-only')
        self.reject(profile=None)

    def test_missing_technical_review_rejected_for_every_profile(self):
        for profile in ('prototype', 'production'):
            with self.subTest(profile=profile):
                self.reject(technical=None, profile=profile)

    def test_production_missing_review(self):
        self.reject(visual=None)

    def test_stale_artifact(self):
        (self.root / 'glb.txt').write_text('changed')
        self.reject()

    def test_stale_context(self):
        for name in ('target', 'runtime', 'camera', 'replay'):
            with self.subTest(name=name):
                path = self.root / (name + '.txt')
                original = path.read_bytes()
                path.write_text('changed')
                self.reject()
                path.write_bytes(original)

    def test_stale_candidate(self):
        self.doc['id'] = 'new-candidate'
        self.write(self.candidate, self.doc)
        self.reject()

    def test_stale_contract(self):
        self.rules['extra'] = 'changed-contract'
        self.write(self.contract, self.rules)
        self.reject()

    def test_stale_evidence(self):
        (self.root / 'proof.txt').write_text('changed')
        self.reject()

    def test_review_failures(self):
        for key, value in [('verdict', 'fail'), ('inspected', False), ('blockers', ['bad']),
                           ('candidate_sha256', '0' * 64), ('contract_sha256', '0' * 64),
                           ('checks', {}), ('reviewer', 'test-builder')]:
            with self.subTest(key=key):
                original = self.reports['visual'][key]
                self.reports['visual'][key] = value
                self.write(self.visual, self.reports['visual'])
                self.reject()
                self.reports['visual'][key] = original
        self.write(self.visual, self.reports['visual'])

    def test_failed_or_incomplete_checks(self):
        for kind, path, name in [('technical', self.technical, 'loads'), ('visual', self.visual, 'matches-target')]:
            for key, value in [('status', 'fail'), ('reason', ''), ('evidence', []), ('evidence', ['missing'])]:
                with self.subTest(kind=kind, key=key, value=value):
                    check = self.reports[kind]['checks'][name]
                    original = check[key]
                    check[key] = value
                    self.write(path, self.reports[kind])
                    self.reject()
                    check[key] = original
                    self.write(path, self.reports[kind])

    def test_path_escape(self):
        for name in ('../glb.txt', '/tmp/glb.txt', './glb.txt', 'x/../glb.txt', 'x\\glb.txt'):
            with self.subTest(name=name):
                self.doc['artifacts']['glb']['path'] = name
                self.write(self.candidate, self.doc)
                self.reject()

    def test_symlink_escape(self):
        with tempfile.TemporaryDirectory() as external:
            target = Path(external) / 'outside'
            target.write_text('outside')
            (self.root / 'escape').symlink_to(target)
            self.doc['artifacts']['glb'] = {'path': 'escape', 'sha256': digest(target.read_bytes())}
            self.write(self.candidate, self.doc)
            self.reject()

    def test_empty_or_incomplete_contract(self):
        for key in ('required_artifacts', 'required_context', 'technical_checks', 'visual_checks'):
            original = self.rules[key]
            self.rules[key] = []
            self.write(self.contract, self.rules)
            self.reject()
            self.rules[key] = original
        self.rules['required_context'] = ['target']
        self.write(self.contract, self.rules)
        self.reject()

    def test_existing_output_untouched(self):
        destination = self.root / 'accepted'
        destination.mkdir()
        sentinel = destination / 'sentinel'
        sentinel.write_text('keep')
        self.reject(output=destination)
        self.assertEqual(sentinel.read_text(), 'keep')
        self.assertEqual(list(destination.iterdir()), [sentinel])

    def test_existing_empty_output_not_replaced(self):
        destination = self.root / 'empty'
        destination.mkdir()
        before = destination.stat().st_ino
        self.reject(output=destination)
        self.assertEqual(before, destination.stat().st_ino)

    def test_publication_race_does_not_replace_output(self):
        from unittest.mock import patch
        import evidence_gate
        original = evidence_gate.rename_exclusive
        destination = self.root / 'raced'
        def race(source, target):
            destination.mkdir()
            (destination / 'winner').write_text('other publisher')
            original(source, target)
        with patch.object(evidence_gate, 'rename_exclusive', race):
            self.reject(output=destination)
        self.assertEqual((destination / 'winner').read_text(), 'other publisher')
        self.assertEqual(len(list(destination.iterdir())), 1)
        self.assertFalse(list(self.root.glob('.evidence-gate-*')))

    def test_rejected_input_never_publishes(self):
        destination = self.root / 'accepted'
        (self.root / 'glb.txt').write_text('changed')
        self.reject(output=destination)
        self.assertFalse(destination.exists())
        self.assertFalse(list(self.root.glob('.evidence-gate-*')))

    def test_malformed_and_duplicate_json(self):
        for content in ('[]', '{"schema":1,"schema":1}', '{broken', '{"schema":true}'):
            self.candidate.write_text(content)
            self.reject()


if __name__ == '__main__':
    unittest.main()
