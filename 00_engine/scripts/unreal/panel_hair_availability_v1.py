"""Fast UI availability from the same family/selected-piece hair policies."""


def denied(family, group, choice):
    if family is None:
        return False
    if family.get('hair_interface', {}).get('deny_all'):
        return True
    if group is None:
        return False
    selected = set(choice.get('slot_choices', {}).values())
    selected.update(choice.get('optional_asset_ids', []))
    selected.update(a['asset_id'] for a in group.get('required_assets', []))
    assets = list(group.get('required_assets', [])) + list(group.get('optional_assets', []))
    assets += [a for options in group.get('slot_options', {}).values() for a in options]
    return any(a['asset_id'] in selected and (a.get('hair_interface') or {}).get('deny_all')
               for a in assets)
