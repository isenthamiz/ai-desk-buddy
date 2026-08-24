"""Renderer-independent face geometry."""

from dataclasses import dataclass
from enum import StrEnum


class MouthShape(StrEnum):
    """Mouth shapes that can be combined with eye expressions."""

    NEUTRAL = "NEUTRAL"
    SMILE = "SMILE"
    OPEN = "OPEN"
    SURPRISED = "SURPRISED"
    THINKING = "THINKING"
    SLEEPING = "SLEEPING"
    WORRIED = "WORRIED"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class FacePose:
    """A complete face pose consumed by presentation adapters."""

    eye_width_scale: float = 1.0
    eye_height_scale: float = 1.0
    eye_tilt_degrees: float = 0.0
    mouth_shape: MouthShape = MouthShape.NEUTRAL
    mouth_openness: float = 0.0
    mouth_width_scale: float = 1.0
    face_y_offset: float = 0.0
