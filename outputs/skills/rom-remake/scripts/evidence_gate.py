#!/usr/bin/env python3
"""Verify pinned review evidence; never generate artistic approvals or modify a game."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tempfile


class GateError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise GateError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f'duplicate JSON key: {key}')
        result[key] = value
    return result


def document(path):
    data = Path(path).read_bytes()
    value = json.loads(data, object_pairs_hook=object_pairs,
                       parse_constant=lambda value: (_ for _ in ()).throw(GateError('invalid JSON constant')))
    require(isinstance(value, dict) and type(value.get('schema')) is int and value['schema'] == 1,
            f'{path}: expected schema 1 object')
    return value, data


def string(value, label):
    require(isinstance(value, str) and bool(value.strip()), f'{label}: expected nonempty string')
    return value


def names(value, label):
    require(isinstance(value, list) and bool(value), f'{label}: expected nonempty list')
    for item in value:
        string(item, label)
    require(len(value) == len(set(value)), f'{label}: duplicate IDs')
    return value


def pinned_files(entries, root, label, collected):
    require(isinstance(entries, dict) and entries, f'{label}: expected nonempty map')
    for key, entry in entries.items():
        string(key, label)
        require(isinstance(entry, dict), f'{label}.{key}: expected object')
        raw = string(entry.get('path'), f'{label}.{key}.path')
        path = PurePosixPath(raw)
        require(not path.is_absolute() and '\\' not in raw and all(p not in ('', '.', '..') for p in raw.split('/')),
                f'{label}.{key}: unsafe relative path')
        source = root.joinpath(*path.parts)
        require(source.resolve().is_relative_to(root.resolve()), f'{label}.{key}: path escapes root')
        require(source.is_file(), f'{label}.{key}: missing file')
        expected = entry.get('sha256')
        require(isinstance(expected, str) and re.fullmatch('[0-9a-f]{64}', expected), f'{label}.{key}: invalid SHA-256')
        data = source.read_bytes()
        require(digest(data) == expected, f'{label}.{key}: stale file hash')
        if raw in collected:
            require(collected[raw] == data, f'{label}.{key}: conflicting path')
        collected[raw] = data


def review(path, kind, candidate_hash, contract_hash, required, author, production):
    report, data = document(path)
    require(report.get('candidate_sha256') == candidate_hash, f'{kind}: stale candidate pin')
    require(report.get('contract_sha256') == contract_hash, f'{kind}: stale contract pin')
    reviewer = string(report.get('reviewer'), f'{kind}.reviewer')
    require(report.get('inspected') is True, f'{kind}: inspection not attested')
    require(report.get('verdict') == 'pass' and report.get('blockers') == [], f'{kind}: verdict or blockers failed')
    if kind == 'visual' and production:
        require(reviewer.strip().casefold() != author.strip().casefold(), 'visual: independent reviewer required')
    files = {}
    pinned_files(report.get('evidence'), Path(path).parent, f'{kind}.evidence', files)
    checks = report.get('checks')
    require(isinstance(checks, dict), f'{kind}: missing checks')
    require(set(required) <= set(checks), f'{kind}: missing required checks')
    for key, check in checks.items():
        require(isinstance(check, dict) and check.get('status') == 'pass', f'{kind}.{key}: failed check')
        string(check.get('reason'), f'{kind}.{key}.reason')
        evidence = names(check.get('evidence'), f'{kind}.{key}.evidence')
        require(set(evidence) <= set(report['evidence']), f'{kind}.{key}: unknown evidence')
    return data, files


def rename_exclusive(source, destination):
    """Atomic directory publication with kernel-enforced no-replace semantics."""
    libc = ctypes.CDLL(None, use_errno=True)
    if sys.platform == 'darwin':
        fn = libc.renamex_np
        fn.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        result = fn(os.fsencode(source), os.fsencode(destination), 4)  # RENAME_EXCL
    elif sys.platform.startswith('linux') and hasattr(libc, 'renameat2'):
        fn = libc.renameat2
        fn.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
        result = fn(-100, os.fsencode(source), -100, os.fsencode(destination), 1)  # RENAME_NOREPLACE
    else:
        raise GateError('atomic no-replace directory publication unsupported on this platform; use check-only')
    if result:
        err = ctypes.get_errno()
        raise GateError(f'publication failed without replacing destination: {os.strerror(err)}')


def gate(candidate, contract, technical, visual=None, profile=None, output=None):
    require(profile in ('prototype', 'production'), 'explicit prototype or production profile required')
    require(technical is not None, 'technical review is required for every profile')
    production = profile == 'production'
    candidate_doc, candidate_data = document(candidate)
    contract_doc, contract_data = document(contract)
    string(candidate_doc.get('id'), 'candidate.id')
    author = string(candidate_doc.get('author'), 'candidate.author')
    names(candidate_doc.get('source_ids'), 'candidate.source_ids')
    required = {key: names(contract_doc.get(key), f'contract.{key}') for key in
                ('required_artifacts', 'required_context', 'technical_checks', 'visual_checks')}
    if production:
        require({'target', 'runtime', 'camera', 'replay'} <= set(required['required_context']),
                'production contract must require target, runtime, camera, replay context')
        require(visual is not None, 'production requires visual review')
    candidate_files = {}
    for kind in ('artifacts', 'context'):
        entries = candidate_doc.get(kind)
        pinned_files(entries, Path(candidate).parent, f'candidate.{kind}', candidate_files)
        require(set(required['required_' + kind]) <= set(entries), f'candidate: missing required {kind}')
    candidate_hash, contract_hash = digest(candidate_data), digest(contract_data)
    bundle = {'candidate/manifest.json': candidate_data, 'contract.json': contract_data}
    for path, data in candidate_files.items():
        require(path != 'manifest.json', 'candidate artifact path collides with bundle manifest')
        bundle['candidate/' + path] = data
    for kind, report_path in [('technical', technical), ('visual', visual)]:
        if report_path is None:
            continue
        data, evidence = review(report_path, kind, candidate_hash, contract_hash,
                                required[kind + '_checks'], author, production)
        bundle[f'reviews/{kind}/report.json'] = data
        for path, payload in evidence.items():
            require(path != 'report.json', f'{kind}: evidence path collides with bundle report')
            bundle[f'reviews/{kind}/' + path] = payload
    # Reject file/directory collisions before attempting to publish.
    for path in bundle:
        require(not any(str(parent) in bundle for parent in PurePosixPath(path).parents), 'bundle path collision')
    record = {'schema': 1, 'candidate_id': candidate_doc['id'], 'profile': profile,
              'status': 'production-evidence-accepted' if production else 'prototype-only',
              'candidate_sha256': candidate_hash, 'contract_sha256': contract_hash,
              'artistic_quality_evaluated_by_checker': False,
              'files': {path: digest(data) for path, data in sorted(bundle.items())}}
    if output is not None:
        destination = Path(output).absolute()
        require(not os.path.lexists(destination), 'output already exists; refusing overwrite')
        require(destination.parent.is_dir(), 'output parent must exist')
        temporary = Path(tempfile.mkdtemp(prefix='.evidence-gate-', dir=destination.parent))
        try:
            for path, data in bundle.items():
                target = temporary / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            (temporary / 'acceptance.json').write_text(json.dumps(record, indent=2) + '\n')
            rename_exclusive(temporary, destination)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('candidate', 'contract', 'technical'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--visual')
    parser.add_argument('--profile', required=True, choices=('prototype', 'production'))
    parser.add_argument('--output', help='new isolated bundle directory; never a live game asset path')
    args = parser.parse_args()
    try:
        print(json.dumps(gate(**vars(args)), indent=2))
    except (GateError, OSError, ValueError, TypeError) as error:
        print(f'evidence gate rejected: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
