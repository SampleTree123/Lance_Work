"""v1 gate cache plus a private geometry.advance dependency injection only."""
import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace

FROZEN = Path(__file__).with_name('cc_refresh_representative_gate_cache_v1.py')
FROZEN_SHA = 'b171f19a98e8f20018bdef62ccb84d901cdfde8db07dfd08849615a1f66f6119'
if hashlib.sha256(FROZEN.read_bytes()).hexdigest() != FROZEN_SHA:
    raise ValueError('Frozen representative gate cache v1 changed')
spec = importlib.util.spec_from_file_location('_geometry_cache_frozen_helper_v1', FROZEN)
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)


def private_geometry_batch(serial, geometry):
    """Original fresh owner, changing only its representative gate function."""
    batch = geometry.owner()
    def representative_gate(plan_path, plan, gate_path):
        # The original direct gate consumes the passed plan. Do not silently
        # substitute a different in-memory document with the cached disk plan.
        if plan != batch.read(plan_path):
            raise ValueError('Geometry representative plan differs from the actual frozen document')
        return serial.representative_evidence(plan_path, gate_path)
    batch.representative_gate = representative_gate
    return batch


class RepresentativeGateCache(original.RepresentativeGateCache):
    def bind(self, serial, order_pin, order_implementation_pins=()):
        super().bind(serial, order_pin, order_implementation_pins)
        geometry = serial.geometry
        proxy = SimpleNamespace(**vars(geometry))
        def advance(*args, **kwargs):
            # Explicit dependency injection, including explicit None, retains
            # the exact original behavior. Only the ordinary omitted case is
            # redirected, and every current-person operation still runs.
            if 'batch' in kwargs:
                return geometry.advance(*args, **kwargs)
            return geometry.advance(*args, batch=private_geometry_batch(serial, geometry), **kwargs)
        proxy.advance = advance
        serial.geometry = proxy
        return serial
