"""Full-length looping CFD40 review; preserves the historical five-second UI.

Technical owner: ANIMATION_EXPRESSION_MORPH.md section 10.
"""
from pathlib import Path
import argparse
import copy
import sys
import motion_library_review_adapter_v1 as base

SCRIPTS = Path(__file__).resolve().parent
RUN = base.extension.RUN.parent / 'full_motion_loop_review_20261009_v1'
CONFIG_SCHEMA = 'cfd40_full_motion_loop_configuration_v1'
POLICY = 'full_body_original_speed_face_five_second_repeat_v1'


def verify_loop_result(result, request):
    if request.get('action') == 'restore':
        return result
    evidence = result.get('full_motion_loop_readback', {})
    if evidence.get('success') is not True or evidence.get('policy') != POLICY:
        raise ValueError('UE did not verify full-length looping playback')
    return result


def controller(motion_record, face_record):
    app = base.controller(motion_record, face_record)
    panel, identities = app.panel, app.identities
    identities.CONFIG_ROOT = RUN / 'configurations'
    identities.face_library.PANEL_RUN = RUN / 'panel'
    panel.WORKER = SCRIPTS / 'ue_cfd40_full_motion_loop_review_endpoint_v1.py'
    old_verify = app.verify_result
    def verify(result, request):
        return verify_loop_result(old_verify(result, request), request)
    app.verify_result = panel.verify_result = verify
    config = app.configurations
    old_build = config.build_configuration
    def build(result, data, validate):
        verify_loop_result(result, result['request'])
        document = old_build(result, data, validate)
        document['schema'] = CONFIG_SCHEMA
        document['review_playback_policy'] = POLICY
        return document
    def load(path, data, validate):
        document = identities.read(path)
        content = document.get('content', {})
        if config.digest(content) != document.get('content_sha256'):
            raise ValueError('Configuration hash differs')
        schema = document.get('schema')
        if schema == CONFIG_SCHEMA and document.get('review_playback_policy') != POLICY:
            raise ValueError('Unknown full-motion playback policy')
        if schema not in (CONFIG_SCHEMA, base.CONFIG_SCHEMA, config.SCHEMA):
            raise ValueError('Unknown configuration schema')
        if content.get('level') != identities.LEVEL or content.get('palette') != data['appearance']:
            raise ValueError('Configuration level/palette differs')
        expected = copy.deepcopy(data['sources'])
        legacy = schema == config.SCHEMA
        if legacy:
            expected.pop('motion_extension')
            expected['native_face_library'] = base.extension.source(base.extension.faces.PANEL_REGISTRY)
        if content.get('sources') != expected:
            raise ValueError('Configuration sources changed')
        request = base.migrate_request(config.portable_request(content['request']), data, from_base=legacy)
        return validate(request, data)
    config.build_configuration, config.load_configuration = build, load
    editor = panel.SexEditor
    class LoopEditor(editor):
        def __init__(self, parent, *args, **kwargs):
            super().__init__(parent, *args, **kwargs)
            parent.winfo_toplevel().title('CFD40 · 完整动作循环审查')
            for widget in parent.master.winfo_children():
                if widget.winfo_class() == 'TLabel' and str(widget.cget('text')).startswith('男女各 20 人'):
                    widget.configure(text='身体动作按完整原时长循环，表情每 5 秒重复；可随时暂停。新搭配首次加载可能较慢。')
            for widget in self.frame.winfo_children():
                if widget.winfo_class() == 'TLabel' and str(widget.cget('text')).startswith('表情（'):
                    widget.configure(text='表情（5 秒重复播放）')
    panel.SexEditor = LoopEditor
    return app


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--motion-catalog', type=Path, required=True)
    parser.add_argument('--face-registry', type=Path, required=True)
    args, remaining = parser.parse_known_args()
    app = controller(base.extension.source(args.motion_catalog), base.extension.source(args.face_registry))
    sys.argv = [sys.argv[0]] + remaining
    app.main()


if __name__ == '__main__':
    main()
