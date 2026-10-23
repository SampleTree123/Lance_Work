"""Scene-panel neutral-base palette and compatibility IDs, without Unreal.

The original/chestnut option retains its source material. Nine dyed options use
one explicit neutral-base method. Rejected comparison IDs are read aliases only;
the soft-reflection experiment is retired and is not promoted into this palette.
"""
ORIGINAL_IDS = ('original', 'black', 'blue', 'pink', 'purple', 'red', 'teal',
                'orange', 'gold', 'silver_white')
TRIAL_IDS = ('black_neutral_v1', 'blue_neutral_v1', 'pink_neutral_v1')
ALIASES = dict(zip(TRIAL_IDS, ('black', 'blue', 'pink')))
NEUTRAL_METHOD = 'neutral_base_v2'
LEGACY_SILVER_ID = 'silver_white_legacy_v1'
SOFT_REFLECTION_METHOD = 'neutral_base_soft_reflection_v1'
SOFT_REFLECTION_COLORS = {'black_soft_reflection_v1': 'black',
                          'blue_soft_reflection_v1': 'blue',
                          'silver_white_soft_reflection_v1': 'silver_white'}
# Keep these names import-compatible with earlier runtime code, but normalize
# all retired choices before they can reach a material factory.
ALIASES.update({LEGACY_SILVER_ID: 'silver_white', **SOFT_REFLECTION_COLORS})
COLOR_LABELS = {'original': '原色', 'black': '黑色', 'blue': '蓝色', 'pink': '粉色',
                'purple': '紫色', 'red': '红色', 'teal': '青色', 'orange': '橙色',
                'gold': '金色', 'silver_white': '白色（微银）'}
# Linear shader multipliers, not display RGB. This separate palette leaves the
# immutable legacy runtime and its historical material specifications intact.
NEUTRAL_TINTS = {
    'black': (.10, .10, .10, 1.), 'blue': (.06, .25, 4., 1.),
    'pink': (2.4, .50, 1.1, 1.), 'purple': (.65, .08, 2.5, 1.),
    'red': (1.8, .035, .06, 1.), 'teal': (.04, 1.1, 1.4, 1.),
    'orange': (3., .65, .015, 1.), 'gold': (3., 2., .10, 1.),
    'silver_white': (4., 4., 4.2, 1.),
}
NEUTRAL_SCALAR_OVERRIDES = {'silver_white': {'Compensate Color Power': .4}}


def canonical_color(identifier):
    return ALIASES.get(identifier, identifier) if isinstance(identifier, str) else identifier


def catalog():
    return [{'id': identifier, 'label': COLOR_LABELS[identifier],
             'method': 'original' if identifier == 'original' else NEUTRAL_METHOD}
            for identifier in ORIGINAL_IDS]
