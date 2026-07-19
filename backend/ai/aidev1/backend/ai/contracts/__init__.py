"""Canonical import location for the frozen shared contracts.

``aidev1.txt`` names ``aidev1/backend/ai/contracts/`` as the shared-contract
path, while the frozen source file lives at ``aidev1/contracts/``. This package
provides re-export shims so both paths resolve to the *same* objects without
modifying or duplicating the frozen contract.
"""
