"""Project wardrive observations onto a canvas from their coordinates.

The map is only the points in the logs. North is up. Longitude is scaled by
the cosine of the mid latitude so a local drive is not stretched. A view can
zoom toward a screen point and pan without using a basemap.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from src.core.wigle_csv import Observation

PlotMark = tuple[float, float, str]
MIN_ZOOM_RATIO = 0.25
MAX_ZOOM_RATIO = 80.0


@dataclass(frozen=True)
class MapSpace:
    """Local east/north positions. Index matches the observation list."""

    xs: tuple[float, ...]
    ys: tuple[float, ...]
    types: tuple[str, ...]

    @classmethod
    def from_observations(cls, observations: Sequence[Observation]) -> MapSpace:
        lats = [float(obs.latitude) for obs in observations]
        lons = [float(obs.longitude) for obs in observations]
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        mid_lat = (min_lat + max_lat) / 2
        lon_scale = math.cos(math.radians(mid_lat))
        if lon_scale < 0.2:
            lon_scale = 0.2
        xs = [(lon - min_lon) * lon_scale for lon in lons]
        ys = [lat - min_lat for lat in lats]
        if max(xs) - min(xs) == 0:
            xs = [0.5] * len(xs)
        if max(ys) - min(ys) == 0:
            ys = [0.5] * len(ys)
        return cls(tuple(xs), tuple(ys), tuple(obs.obs_type for obs in observations))

    @property
    def span_x(self) -> float:
        if not self.xs:
            return 1.0
        span = max(self.xs) - min(self.xs)
        return span if span else 1.0

    @property
    def span_y(self) -> float:
        if not self.ys:
            return 1.0
        span = max(self.ys) - min(self.ys)
        return span if span else 1.0


@dataclass(frozen=True)
class MapView:
    """Screen transform. Local (0, 0) sits at ``(origin_x, origin_y)``."""

    origin_x: float
    origin_y: float
    scale: float


def fit_view(
    space: MapSpace,
    width: float,
    height: float,
    pad: float = 28,
) -> MapView:
    """Frame every point inside the padded canvas."""
    usable_w = max(width - pad * 2, 1)
    usable_h = max(height - pad * 2, 1)
    span_x = max(space.xs) - min(space.xs) or 1.0
    span_y = max(space.ys) - min(space.ys) or 1.0
    scale = min(usable_w / span_x, usable_h / span_y)
    origin_x = pad + (usable_w - span_x * scale) / 2
    origin_y = pad + (usable_h + span_y * scale) / 2
    return MapView(origin_x=origin_x, origin_y=origin_y, scale=scale)


def screen_marks(space: MapSpace, view: MapView) -> list[PlotMark]:
    marks: list[PlotMark] = []
    for x, y, obs_type in zip(space.xs, space.ys, space.types, strict=True):
        marks.append((view.origin_x + x * view.scale, view.origin_y - y * view.scale, obs_type))
    return marks


def project_observations(
    observations: Sequence[Observation],
    width: float,
    height: float,
    pad: float = 28,
) -> list[PlotMark]:
    """Return ``(x, y, type)`` canvas marks fitted to the canvas."""
    if not observations or width <= pad * 2 or height <= pad * 2:
        return []
    space = MapSpace.from_observations(observations)
    return screen_marks(space, fit_view(space, width, height, pad))


def zoom_view(
    view: MapView,
    anchor_x: float,
    anchor_y: float,
    factor: float,
    fit_scale: float,
) -> MapView:
    """Zoom toward a screen point. The local point under the anchor stays put."""
    if factor <= 0 or fit_scale <= 0:
        return view
    scale = view.scale * factor
    low = fit_scale * MIN_ZOOM_RATIO
    high = fit_scale * MAX_ZOOM_RATIO
    scale = min(max(scale, low), high)
    local_x = (anchor_x - view.origin_x) / view.scale
    local_y = (view.origin_y - anchor_y) / view.scale
    return MapView(
        origin_x=anchor_x - local_x * scale,
        origin_y=anchor_y + local_y * scale,
        scale=scale,
    )


def pan_view(view: MapView, dx: float, dy: float) -> MapView:
    """Move the map with a screen drag. Positive dx shifts content to the right."""
    return MapView(origin_x=view.origin_x + dx, origin_y=view.origin_y + dy, scale=view.scale)


def hits_near(marks: Sequence[PlotMark], x: float, y: float, radius: float) -> list[int]:
    """Indexes of marks within ``radius`` pixels, nearest first."""
    limit = radius * radius
    found: list[tuple[float, int]] = []
    for index, (mx, my, _obs_type) in enumerate(marks):
        distance = (mx - x) ** 2 + (my - y) ** 2
        if distance <= limit:
            found.append((distance, index))
    found.sort()
    return [index for _distance, index in found]
