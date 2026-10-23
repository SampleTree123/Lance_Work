"""Build a new review catalog/overlay from actual evidence, without activating it.

Technical owner: ANIMATION_EXPRESSION_MORPH.md section 9.
"""
import argparse
import json
from pathlib import Path

import complete_character_slot_review_contract_v1 as base_contract
import motion_library_extension_contract_v1 as extension


def write_new(path, document):
    path = Path(path).resolve()
    if not path.is_relative_to(extension.RUN.resolve()) or path.suffix != '.json':
        raise ValueError('New output must be a JSON inside the motion expansion run')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(document, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    return extension.source(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operation', required=True)
    motion = sub.add_parser('motions')
    motion.add_argument('--pairs', type=Path, required=True, help='JSON object with pairs list')
    motion.add_argument('--output', type=Path, required=True)
    face = sub.add_parser('faces')
    face.add_argument('--motion-catalog', type=Path, required=True)
    face.add_argument('--reports', type=Path, required=True, help='JSON object with composition_reports list of SHA records')
    face.add_argument('--root-visual', type=Path, required=True)
    face.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Refusing existing output; choose a new version filename')
    base = base_contract.catalog()
    if args.operation == 'motions':
        document = extension.build_motion_document(extension.read(args.pairs)['pairs'], base)
    else:
        motions = extension.motion_catalog(args.motion_catalog, base)
        document = extension.build_face_document(motions,
            extension.read(args.reports)['composition_reports'], extension.source(args.root_visual))
    record = write_new(args.output, document)
    print(json.dumps({'written': record, 'activated': False, 'schema': document['schema']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
