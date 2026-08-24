"""Pygame adapter for the virtual Desk Buddy display."""

import math

import pygame

from aideskbuddy_simulator.config import DisplayConfig
from aideskbuddy_simulator.core.state import DeskBuddyState
from aideskbuddy_simulator.face.controller import Expression, FaceController

BACKGROUND = pygame.Color("#07131F")
EYE_COLOR = pygame.Color("#8EEBFF")
PUPIL_COLOR = pygame.Color("#07131F")
STATUS_COLOR = pygame.Color("#527080")
ERROR_COLOR = pygame.Color("#FF647C")
INDICATOR_COLOR = pygame.Color("#F6D365")


class FaceRenderer:
    """Draw face animation state onto a virtual display surface."""

    def __init__(self, config: DisplayConfig) -> None:
        self._config = config
        self._font = pygame.font.Font(None, 18)

    def render(
        self,
        surface: pygame.Surface,
        face: FaceController,
        state: DeskBuddyState,
        *,
        timer_text: str = "--:--",
        timer_status_text: str | None = None,
        notification_text: str | None = None,
        buddy_text: str | None = None,
        connection_status: str = "OFFLINE",
        debug_input_label: str | None = None,
        debug_input_text: str = "",
        show_help: bool = False,
    ) -> None:
        surface.fill(BACKGROUND)
        color = ERROR_COLOR if face.expression is Expression.ERROR else EYE_COLOR
        gaze_x, gaze_y = face.gaze_offset
        self._draw_eye(
            surface,
            center_x=105,
            openness=face.eye_openness,
            scale=face.eye_scale,
            gaze=(gaze_x, gaze_y),
            color=color,
        )
        self._draw_eye(
            surface,
            center_x=215,
            openness=face.eye_openness,
            scale=face.eye_scale,
            gaze=(gaze_x, gaze_y),
            color=color,
        )
        self._draw_state_indicator(
            surface,
            face,
            timer_text=timer_text,
            timer_status_text=timer_status_text,
            notification_text=notification_text,
            buddy_text=buddy_text,
        )

        if buddy_text and face.expression is not Expression.SURPRISED:
            self._draw_notification_message(surface, buddy_text)

        label = self._font.render(state.value, True, STATUS_COLOR)
        label_rect = label.get_rect(
            center=(self._config.virtual_width // 2, 211)
        )
        surface.blit(label, label_rect)
        self._draw_connection_status(surface, connection_status)
        if debug_input_label is not None:
            self._draw_text_input(surface, debug_input_label, debug_input_text)
        if show_help:
            self._draw_help(surface)
        else:
            help_hint = self._font.render("?: HELP", True, STATUS_COLOR)
            surface.blit(help_hint, (255, 219))

    @staticmethod
    def _draw_eye(
        surface: pygame.Surface,
        *,
        center_x: int,
        openness: float,
        scale: float,
        gaze: tuple[float, float],
        color: pygame.Color,
    ) -> None:
        center_y = 115
        width = round(72 * scale)
        full_height = round(92 * scale)
        height = max(4, round(full_height * openness))
        eye_rect = pygame.Rect(0, 0, width, height)
        eye_rect.center = (center_x, center_y)

        if openness <= 0.06:
            pygame.draw.line(
                surface,
                color,
                (center_x - width // 2, center_y),
                (center_x + width // 2, center_y),
                width=4,
            )
            return

        pygame.draw.ellipse(surface, color, eye_rect)
        pupil_radius = max(3, round(13 * openness))
        pupil_center = (
            round(center_x + gaze[0]),
            round(center_y + gaze[1]),
        )
        pygame.draw.circle(surface, PUPIL_COLOR, pupil_center, pupil_radius)

    def _draw_state_indicator(
        self,
        surface: pygame.Surface,
        face: FaceController,
        *,
        timer_text: str,
        timer_status_text: str | None,
        notification_text: str | None,
        buddy_text: str | None,
    ) -> None:
        elapsed = face.animation_elapsed
        center_x = self._config.virtual_width // 2

        if face.expression is Expression.LISTENING:
            radius = 7 + round(2 * abs(math.sin(elapsed * 4)))
            pygame.draw.circle(surface, INDICATOR_COLOR, (center_x, 35), radius, 2)
        elif face.expression is Expression.THINKING:
            active_dot = int(elapsed * 3) % 3
            for index, x in enumerate((146, 160, 174)):
                radius = 4 if index == active_dot else 2
                pygame.draw.circle(surface, INDICATOR_COLOR, (x, 35), radius)
        elif face.expression is Expression.SPEAKING:
            if not buddy_text:
                for index, x in enumerate((150, 160, 170)):
                    height = 6 + round(8 * abs(math.sin(elapsed * 7 + index)))
                    pygame.draw.line(
                        surface,
                        INDICATOR_COLOR,
                        (x, 35 - height // 2),
                        (x, 35 + height // 2),
                        3,
                    )
        elif face.expression is Expression.TIMER:
            timer = self._font.render(timer_text, True, INDICATOR_COLOR)
            surface.blit(timer, timer.get_rect(center=(center_x, 35)))
            if timer_status_text:
                status = self._font.render(timer_status_text, True, INDICATOR_COLOR)
                surface.blit(status, status.get_rect(center=(center_x, 55)))
        elif face.expression is Expression.SURPRISED:
            self._draw_notification_message(surface, notification_text or "!")
        elif face.expression is Expression.SLEEPING:
            marker = self._font.render("z Z", True, EYE_COLOR)
            surface.blit(marker, marker.get_rect(center=(250, 55)))
        elif face.expression is Expression.ERROR:
            marker = self._font.render("! ERROR", True, ERROR_COLOR)
            surface.blit(marker, marker.get_rect(center=(center_x, 35)))
        elif face.expression is Expression.HAPPY:
            pygame.draw.aalines(
                surface,
                EYE_COLOR,
                False,
                [(130, 152), (145, 161), (160, 164), (175, 161), (190, 152)],
            )

    def _draw_notification_message(
        self,
        surface: pygame.Surface,
        text: str,
    ) -> None:
        lines = self._wrap_text(text, max_width=280, max_lines=2)
        for index, line in enumerate(lines):
            rendered = self._font.render(line, True, INDICATOR_COLOR)
            surface.blit(rendered, rendered.get_rect(center=(160, 25 + index * 17)))

    def _draw_text_input(
        self,
        surface: pygame.Surface,
        label: str,
        text: str,
    ) -> None:
        panel = pygame.Rect(8, 178, 304, 54)
        pygame.draw.rect(surface, pygame.Color("#102635"), panel, border_radius=5)
        pygame.draw.rect(surface, STATUS_COLOR, panel, width=1, border_radius=5)
        prompt = self._font.render(f"{label} >", True, INDICATOR_COLOR)
        surface.blit(prompt, (16, 187))
        prompt_width = prompt.get_width() + 8
        available_width = 288 - prompt_width
        display_text = self._fit_text(text or "Type message...", available_width)
        value = self._font.render(display_text, True, EYE_COLOR)
        surface.blit(value, (16 + prompt_width, 187))
        help_text = self._font.render("Enter: send   Esc: cancel", True, STATUS_COLOR)
        surface.blit(help_text, (16, 210))

    def _draw_connection_status(
        self,
        surface: pygame.Surface,
        status: str,
    ) -> None:
        connected = status == "CONNECTED"
        color = pygame.Color("#42D392") if connected else ERROR_COLOR
        pygame.draw.circle(surface, color, (13, 226), 3)
        label = self._font.render(status, True, STATUS_COLOR)
        surface.blit(label, (21, 219))

    def _draw_help(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((4, 14, 23, 242))
        surface.blit(overlay, (0, 0))

        title = self._font.render("SIMULATOR CONTROLS", True, INDICATOR_COLOR)
        surface.blit(title, (14, 12))
        help_text_color = pygame.Color("#8AAABB")

        sections = [
            (
                14,
                "EVENTS / INPUT",
                ["F  Button", "P  Presence", "T  Talk / text", "N  Notification"],
            ),
            (
                164,
                "STATE PREVIEW",
                ["1 IDLE     2 LISTEN", "3 THINK    4 SPEAK", "5 TIMER    6 NOTIFY", "7 SLEEP    8 ERROR"],
            ),
            (
                14,
                "TIMER",
                ["Up/Down  Duration", "Enter  Start", "Space  Pause/resume", "C  Cancel"],
            ),
            (
                164,
                "FACE",
                ["W/A/S/D  Look", "X  Center", "B  Blink", "H  Happy"],
            ),
        ]
        for index, (x, heading, lines) in enumerate(sections):
            y = 43 if index < 2 else 133
            heading_surface = self._font.render(heading, True, EYE_COLOR)
            surface.blit(heading_surface, (x, y))
            for line_index, line in enumerate(lines):
                line_surface = self._font.render(line, True, help_text_color)
                surface.blit(line_surface, (x, y + 18 + line_index * 15))

        footer = self._font.render("? / F1  Close help     Esc  Quit", True, INDICATOR_COLOR)
        surface.blit(footer, footer.get_rect(center=(160, 226)))

    def _wrap_text(
        self,
        text: str,
        *,
        max_width: int,
        max_lines: int,
    ) -> list[str]:
        words = text.split()
        if not words:
            return [""]
        lines: list[str] = []
        current = words[0]
        for index, word in enumerate(words[1:], start=1):
            candidate = f"{current} {word}"
            if self._font.size(candidate)[0] <= max_width:
                current = candidate
                continue
            lines.append(self._fit_text(current, max_width))
            if len(lines) == max_lines - 1:
                current = " ".join(words[index:])
                break
            current = word
        lines.append(self._fit_text(current, max_width))
        return lines[:max_lines]

    def _fit_text(self, text: str, max_width: int) -> str:
        if self._font.size(text)[0] <= max_width:
            return text
        shortened = text
        while shortened and self._font.size(f"{shortened}…")[0] > max_width:
            shortened = shortened[:-1]
        return f"{shortened}…"


def scale_to_window(
    virtual_display: pygame.Surface,
    window: pygame.Surface,
) -> None:
    """Scale and center the virtual display without changing its aspect ratio."""
    virtual_width, virtual_height = virtual_display.get_size()
    window_width, window_height = window.get_size()
    scale = min(window_width / virtual_width, window_height / virtual_height)
    scaled_size = (
        max(1, round(virtual_width * scale)),
        max(1, round(virtual_height * scale)),
    )
    scaled = pygame.transform.smoothscale(virtual_display, scaled_size)
    destination = scaled.get_rect(center=window.get_rect().center)
    window.fill(pygame.Color("black"))
    window.blit(scaled, destination)
