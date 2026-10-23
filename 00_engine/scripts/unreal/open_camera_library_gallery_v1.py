"""Local-only review launcher. Owner: SCENE_CAMERA_SEQUENCE.md section 8."""
from pathlib import Path
import open_camera_pilot_gallery_v1 as base

if __name__ == '__main__':
    base.DEFAULT_RUN = Path('D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/camera_library_expansion_20261010_v1')
    base.PORT = 8877
    base.URL = 'http://127.0.0.1:8877/gallery/index.html'
    base.main()
