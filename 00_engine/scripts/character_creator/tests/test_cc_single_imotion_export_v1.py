"""Test explicit iMotion opt-in without importing the CC application."""
import ast
import hashlib
import os
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1]/'cc_validate_body_reconstruction.py'
TREE = ast.parse(SOURCE.read_text(encoding='utf-8-sig'))
CODE = compile(ast.Module(body=[n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name in ('_animation_p0_verified_file', 'validate_single_motion_export_source')], type_ignores=[]), str(SOURCE), 'exec')


@pytest.fixture
def setup(tmp_path):
    def canonical(path, label):
        p = Path(path).resolve()
        if not p.is_file(): raise ValueError('missing source')
        return str(p)
    def suffix(path, extension, label):
        if Path(path).suffix.lower() != extension: raise ValueError('wrong extension')
    sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
    env = dict(os=os, SCRIPT_DIR=str(tmp_path), ReconstructionError=ValueError, canonical_existing_file=canonical, require_file_extension=suffix, sha256_file=sha)
    exec(CODE, env)
    p = tmp_path/'runtime_staging/motion_library_expansion_20261009_v1/motion_copies/MOTION_CAND_002/GettingReady.iMotion'
    p.parent.mkdir(parents=True); p.write_bytes(b'original-imotion-no-renaming')
    record = {'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha(p)}
    return env, {'motion_path': str(p), 'allow_imotion': True, 'motion_source': record}, tmp_path


def test_opt_in_imotion_uses_exact_original_extension_and_hash(setup):
    env, payload, _ = setup
    assert env['validate_single_motion_export_source'](payload) == payload['motion_path']


@pytest.mark.parametrize('mutation', ['omitted_optin', 'false_optin', 'non_bool', 'missing_record', 'missing_sha', 'changed_sha', 'changed_size', 'bool_size', 'outside', 'mismatched_path', 'unsupported_suffix'])
def test_rejects_invalid_opt_in(setup, mutation):
    env, payload, tmp = setup
    if mutation == 'omitted_optin': payload.pop('allow_imotion')
    elif mutation == 'false_optin': payload['allow_imotion'] = False
    elif mutation == 'non_bool': payload['allow_imotion'] = 'true'
    elif mutation == 'missing_record': payload.pop('motion_source')
    elif mutation == 'missing_sha': payload['motion_source'].pop('sha256')
    elif mutation == 'changed_sha': payload['motion_source']['sha256'] = '0'*64
    elif mutation == 'changed_size': payload['motion_source']['bytes'] += 1
    elif mutation == 'bool_size': payload['motion_source']['bytes'] = True
    elif mutation == 'outside':
        p = tmp/'outside.iMotion'; p.write_bytes(b'other'); payload['motion_path'] = str(p)
    elif mutation == 'mismatched_path':
        p = Path(payload['motion_path']).with_name('different.iMotion'); p.write_bytes(b'original-imotion-no-renaming'); payload['motion_source']['path'] = str(p)
    elif mutation == 'unsupported_suffix':
        p = Path(payload['motion_path']).with_suffix('.iMotionPlus'); p.write_bytes(b'other'); payload['motion_path'] = str(p)
    with pytest.raises(ValueError): env['validate_single_motion_export_source'](payload)


def test_legacy_rlmotion_needs_no_new_flag_or_record(setup):
    env, _, tmp = setup
    p = tmp/'legacy.rlMotion'; p.write_bytes(b'legacy')
    assert env['validate_single_motion_export_source']({'motion_path': str(p)}) == str(p)
