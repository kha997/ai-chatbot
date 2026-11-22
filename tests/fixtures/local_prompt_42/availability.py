"""Synthetic coding prompt fixture. Intervals are half-open."""


def combine_windows(windows):
    merged = []
    for start, end in sorted(windows):
        if merged:
            if start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
                continue
        merged.append((start, end))
    return merged
