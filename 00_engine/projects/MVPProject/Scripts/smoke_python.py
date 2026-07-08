import unreal


def main():
    unreal.log("DATAMAKE_UE_PYTHON_SMOKE_BEGIN")
    try:
        engine_version = unreal.SystemLibrary.get_engine_version()
    except Exception as exc:
        engine_version = f"unavailable: {exc!r}"

    unreal.log(f"DATAMAKE_ENGINE_VERSION={engine_version}")
    unreal.log(f"DATAMAKE_PROJECT_DIR={unreal.Paths.project_dir()}")
    unreal.log(f"DATAMAKE_PROJECT_SAVED_DIR={unreal.Paths.project_saved_dir()}")
    unreal.log("DATAMAKE_UE_PYTHON_SMOKE_OK")


if __name__ == "__main__":
    main()
