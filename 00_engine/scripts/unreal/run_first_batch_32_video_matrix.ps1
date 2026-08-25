$ErrorActionPreference = "Stop"
$runner = Join-Path $PSScriptRoot "run_first_batch_render_matrix.py"
python $runner @args
exit $LASTEXITCODE
