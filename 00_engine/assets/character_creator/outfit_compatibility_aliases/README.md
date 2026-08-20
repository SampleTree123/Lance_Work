# Outfit Compatibility Aliases

This directory contains byte-identical loader aliases for Character Creator
assets whose original filename extension is not accepted by the public RLPy
loading entry point.

`compatibility_alias_registry.json` is authoritative. An alias is valid only
when its size and SHA-256 match the immutable source asset exactly. These files
do not modify geometry, skin weights, materials, or metadata; only the filename
extension used for CC loader dispatch differs.
