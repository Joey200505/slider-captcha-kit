"""Bounded eased pointer motion; never crosses the supplied travel limit."""
import math
import random


def drag_points(distance: float, *, rng: random.Random | None = None,
                available_distance: float | None = None) -> list[tuple[float,float,int]]:
    if not math.isfinite(distance) or distance <= 0:
        raise ValueError("DRAG_DISTANCE_INVALID")
    limit = available_distance if available_distance is not None else distance+8
    if not math.isfinite(limit) or limit < distance:
        raise ValueError("DRAG_LIMIT_INVALID")
    rng = rng or random.Random()
    count, duration = rng.randint(25,45), rng.randint(700,1400)
    overshoot = min(rng.uniform(3,8), limit-distance)
    forward = count-4
    positions = [(min(limit,(distance+overshoot)*(1-(1-i/forward)**3)),rng.uniform(-2,2))
                 for i in range(1,forward+1)]
    positions.extend((distance+overshoot*(1-i/4),0.0 if i==4 else rng.uniform(-2,2)) for i in range(1,5))
    weights = [rng.uniform(0.7,1.3) for _ in positions]
    total = sum(weights)
    delays = [int(duration*w/total) for w in weights]
    delays[-1] += duration-sum(delays)
    return [(x,y,d) for (x,y),d in zip(positions,delays)]
