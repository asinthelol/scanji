# Manga reading order (right-to-left, top-to-bottom) for a set of rectangles.
Rect = tuple[float, float, float, float]  # x, y, w, h


def _groups(rects: list[Rect], idx: list[int], axis: int) -> list[list[int]]:
    """
    Split idx into groups separated by empty gaps along one axis (0 = x, 1 = y).
    """
    ordered = sorted(idx, key=lambda i: rects[i][axis])
    groups: list[list[int]] = []
    reach = float("-inf")
    for i in ordered:
        start, end = rects[i][axis], rects[i][axis] + rects[i][axis + 2]
        if not groups or start > reach:
            groups.append([])
        groups[-1].append(i)
        reach = max(reach, end)
    return groups


def _split(rects: list[Rect], idx: list[int]) -> list[int]:
    if len(idx) <= 1:
        return idx
    
    # Panels are usually separated by gutters, so cut a
    # horizontal gap first (top to bottom), then a vertical one (right to left).
    for axis in (1, 0):
        groups = _groups(rects, idx, axis)
        if len(groups) > 1:
            if axis == 0:
                groups.reverse()
            return [i for g in groups for i in _split(rects, g)]
        
    # If no clean cut, fall back to top row first, right to left.
    return sorted(idx, key=lambda i: (rects[i][1] + rects[i][3] / 2, -(rects[i][0] + rects[i][2] / 2)))


def reading_order(rects: list[Rect]) -> list[int]:
    """
    Indices of rects in manga reading order.
    """
    return _split(rects, list(range(len(rects))))
