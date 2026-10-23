"""Private panel policy: site intent survives review-stamp changes."""
import copy
import json


def site_key(state):
    if not state.get('site_id') or not state.get('map'):
        return ''
    return json.dumps({'map': state['map'], 'site_id': state['site_id']},
                      ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def exclusions(rows):
    return [copy.deepcopy(r) for r in rows if r.get('decision') == 'excluded']


def current_draft(record, state):
    result = copy.deepcopy(record)
    if result.get('review_stamp') != state.get('review_stamp'):
        result['allowed_combinations'] = exclusions(result.get('allowed_combinations', []))
        result['issue_reviews'] = {}
    return result


def install(app):
    """Changes only the privately loaded pair panel; no UE or asset operations."""
    if getattr(app, '_site_intent_drafts_installed', False):
        return
    app.site_signature = site_key
    original = app.Panel

    class SiteIntentPanel(original):
        def remember_draft(self):
            key = site_key(self.state)
            if key and self.decisions_dirty:
                self.drafts[key] = {
                    'site_id': self.state['site_id'], 'map': self.state['map'],
                    'review_stamp': self.state.get('review_stamp'),
                    'allowed_combinations': app.decision_rows(self.decisions),
                    'issue_reviews': app.issue_review_rows(self.issue_reviews),
                    'updated_at': app.now()}
                app.write(self.drafts_path, self.drafts)

        def send(self, action, **values):
            if action in {'save_site', 'check_all', 'check_start'}:
                values.update(decision_site_id=self.state.get('site_id'),
                              decision_map=self.state.get('map'))
            return super().send(action, **values)

        def apply(self, reply, action):
            incoming = reply.get('state')
            if isinstance(incoming, dict):
                key = site_key(incoming)
                same_site = bool(key) and key == site_key(self.state)
                changed = self.state.get('review_stamp') != incoming.get('review_stamp')
                if same_site and changed:
                    # Keep exclusions, but never carry an old pass/issue verdict
                    # to a changed location, appearance, or checker version.
                    self.decisions = exclusions(self.decisions)
                    self.issue_reviews, self.undo_decisions = {}, []
                    self.decisions_dirty = True
                if key in self.drafts:
                    self.drafts[key] = current_draft(self.drafts[key], incoming)
            result = super().apply(reply, action)
            self.remember_draft()
            return result

    app.Panel = SiteIntentPanel
    app._site_intent_drafts_installed = True
