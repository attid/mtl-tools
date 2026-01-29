"""Utility functions migrated from global_data."""


def float2str(f) -> str:
    """Convert float to string, removing trailing zeros."""
    if isinstance(f, str):
        f = f.replace(',', '.')
        f = float(f)
    s = "%.7f" % f
    while len(s) > 1 and s[-1] in ('0', '.'):
        last = s[-1]
        s = s[0:-1]
        if last == '.':
            break
    return s


def str2float(f) -> float:
    """Convert string to float via float2str normalization."""
    return float(float2str(f))
