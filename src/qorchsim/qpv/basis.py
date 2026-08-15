"""QPV basis functions."""


def xor_basis(x: int, y: int) -> int:
    """Return the BB84 basis bit x XOR y."""
    if x not in (0, 1) or y not in (0, 1):
        raise ValueError("basis inputs must be bits")
    return x ^ y
