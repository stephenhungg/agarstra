"""Cross-language consumer tests using temporary, explicitly synthetic approvals."""
import json
from pathlib import Path
import subprocess
import unittest

import assemble_runtime as assembler
import test_assemble_runtime as fixtures


class ConsumerChainTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.AssemblyTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        second = self.fixture.fixture('synthetic-b')
        fixtures.write_json(self.fixture.plan, {'schema': 1, 'entries': [
            {'bundle': str(self.fixture.bundle)}, {'bundle': str(second)}]})
        self.fixture.assemble()
        self.registry = json.loads(self.fixture.pointer.read_bytes())

    def consume(self, runtime_hash=None):
        module = (assembler.APP / 'src/production-gate.js').as_uri()
        script = '''
import fs from 'node:fs/promises';
import path from 'node:path';
import {verifyRegistry, parseDocument} from %s;
const root = process.argv[1];
const registry = parseDocument(await fs.readFile(path.join(root, 'photoreal-registry.json')));
try {
  const verified = await verifyRegistry(registry, async relative => new Uint8Array(await fs.readFile(path.join(root, relative))), {expectedRuntimeHash: process.argv[2]});
  console.log(JSON.stringify({ids: [...verified.keys()], byteLengths: [...verified.values()].map(value => value.bytes.length)}));
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
''' % json.dumps(module)
        return subprocess.run(['node', '--input-type=module', '-e', script,
                               str(self.fixture.assets), runtime_hash or assembler.digest(self.fixture.runtime)],
                              capture_output=True, text=True, timeout=30)

    def assert_rejected(self, message):
        result = self.consume()
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(message, result.stderr)

    def test_python_published_two_bundles_are_consumed_by_javascript(self):
        result = self.consume()
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value['ids'], ['synthetic-a', 'synthetic-b'])
        self.assertTrue(all(length > 20 for length in value['byteLengths']))

    def test_tampered_published_artifact_rejected(self):
        path = self.fixture.assets / self.registry['entries'][1]['path']
        path.write_bytes(path.read_bytes() + b'tampered synthetic bytes')
        self.assert_rejected('stale file hash')

    def test_tampered_published_review_evidence_rejected(self):
        bundle = self.fixture.assets / self.registry['entries'][0]['bundle']
        (bundle / 'reviews/visual/proof.txt').write_text('changed synthetic evidence')
        self.assert_rejected('stale file hash')

    def test_running_runtime_mismatch_rejected(self):
        result = self.consume(assembler.digest(b'different synthetic runtime'))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('registry runtime mismatch', result.stderr)

    def test_forged_registry_runtime_cannot_reuse_old_review(self):
        self.registry['runtime_sha256'] = assembler.digest(b'different synthetic runtime')
        fixtures.write_json(self.fixture.pointer, self.registry)
        result = self.consume(self.registry['runtime_sha256'])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('reviewed runtime differs', result.stderr)

    def test_registry_cannot_remap_reviewed_asset_identity(self):
        self.registry['entries'][0]['id'] = 'synthetic-renamed'
        fixtures.write_json(self.fixture.pointer, self.registry)
        self.assert_rejected('runtime mapping differs')


if __name__ == '__main__':
    unittest.main()
