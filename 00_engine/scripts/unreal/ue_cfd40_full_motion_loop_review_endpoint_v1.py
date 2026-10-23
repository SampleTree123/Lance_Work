"""Guarded root-only full motion loop endpoint.

Technical owner: ANIMATION_EXPRESSION_MORPH.md section 10.
"""
import json
import uuid
import motion_library_review_adapter_v1 as base
import ue_cfd40_full_motion_loop_v1 as loops


def run(request, motion_record, face_record):
    app = base.worker(motion_record, face_record)
    loops.install_worker(app)
    try:
        result = app.run(request)
        path = app.review.write('replies/' + uuid.uuid4().hex + '.json', result)
        print(app.review.MARKER + json.dumps({'success': result.get('success', False), 'result_file': str(path)}))
        return result
    except Exception as exc:
        app.review.write('last_error.json', {'success': False, 'at': app.legacy.now(), 'error': str(exc)})
        raise


if __name__ == '__main__':
    run(globals()['DM_SLOT_REVIEW_REQUEST'], globals()['DM_MOTION_CATALOG'], globals()['DM_MOTION_FACE_REGISTRY'])
