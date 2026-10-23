"""Photo/raw-Headshot project -> Average body and fixed head, native appearance.

Default preparation only. Explicit --execute drives the already-open offline CC.
No library skin, eyebrow, eyelash, iris, teeth or material assembly is selected.
"""
import sys

from run_cc_character_creation_v1 import main as creation_main
from cc_character_creation_job_state_v1 import ControllerError


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    if any(argument == '--appearance-mode' or argument.startswith('--appearance-mode=') for argument in arguments):
        raise ControllerError('This entry fixes appearance_mode=headshot_native; use the assembled entry for other modes')
    return creation_main(arguments, fixed_appearance_mode='headshot_native', description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
