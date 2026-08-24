"""Pygame adapter for the round virtual Desk Buddy display."""

import math

import pygame

from aideskbuddy_simulator.config import DisplayConfig
from aideskbuddy_simulator.core.state import DeskBuddyState
from aideskbuddy_simulator.face.controller import Expression, FaceController
from aideskbuddy_simulator.face.pose import FacePose, MouthShape

OUTSIDE_COLOR = pygame.Color("#010407")
SCREEN_COLOR = pygame.Color("#041015")
SCREEN_RIM = pygame.Color("#28515B")
PHOSPHOR = pygame.Color("#72F7F1")
PHOSPHOR_CORE = pygame.Color("#C4FFFC")
STATUS_COLOR = pygame.Color("#60949D")
ERROR_COLOR = pygame.Color("#FF647C")
INDICATOR_COLOR = pygame.Color("#F6D365")
CONNECTED_COLOR = pygame.Color("#42D392")


class FaceRenderer:
    """Draw a pixel-phosphor face onto a circular virtual display."""

    def __init__(self, config: DisplayConfig) -> None:
        self._config = config
        self._font = pygame.font.Font(None, 18)
        self._small_font = pygame.font.Font(None, 15)
        self._tiny_font = pygame.font.Font(None, 13)
        self._center = (config.virtual_width // 2, config.virtual_height // 2)
        self._radius = min(config.virtual_width, config.virtual_height) // 2 - 3

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
        surface.fill(OUTSIDE_COLOR)
        self._draw_round_screen(surface)

        color = ERROR_COLOR if face.expression is Expression.ERROR else PHOSPHOR
        pose = face.pose
        gaze_x, gaze_y = face.gaze_offset
        self._draw_eye(
            surface,
            center=(76 + round(gaze_x), 94 + round(gaze_y + pose.face_y_offset)),
            openness=face.eye_openness,
            pose=pose,
            color=color,
            side=-1,
        )
        self._draw_eye(
            surface,
            center=(164 + round(gaze_x), 94 + round(gaze_y + pose.face_y_offset)),
            openness=face.eye_openness,
            pose=pose,
            color=color,
            side=1,
        )
        self._draw_mouth(surface, pose, color)
        self._draw_state_indicator(
            surface,
            face,
            timer_text=timer_text,
            timer_status_text=timer_status_text,
            notification_text=notification_text,
            buddy_text=buddy_text,
        )

        if buddy_text and face.expression is not Expression.SURPRISED:
            self._draw_centered_message(surface, buddy_text)

        label = self._small_font.render(state.value, True, STATUS_COLOR)
        surface.blit(label, label.get_rect(center=(120, 193)))
        self._draw_connection_arc(surface, connection_status)

        if debug_input_label is not None:
            self._draw_text_input(surface, debug_input_label, debug_input_text)
        if show_help:
            self._draw_help(surface)

        self._draw_scanlines(surface)
        pygame.draw.circle(surface, SCREEN_RIM, self._center, self._radius, 2)

    def _draw_round_screen(self, surface: pygame.Surface) -> None:
        pygame.draw.circle(surface, SCREEN_RIM, self._center, self._radius + 1)
        pygame.draw.circle(surface, SCREEN_COLOR, self._center, self._radius - 2)
        pygame.draw.arc(
            surface,
            pygame.Color("#477983"),
            pygame.Rect(10, 10, 220, 220),
            math.radians(48),
            math.radians(132),
            1,
        )

    @staticmethod
    def _draw_eye(
        surface: pygame.Surface,
        *,
        center: tuple[int, int],
        openness: float,
        pose: FacePose,
        color: pygame.Color,
        side: int,
    ) -> None:
        cell = 6
        pitch = 7
        columns = max(5, round(9 * pose.eye_width_scale))
        rows = max(1, round(5 * pose.eye_height_scale * openness))
        rotation = math.radians(pose.eye_tilt_degrees * side)
        glow = pygame.Surface(surface.get_size(), pygame.SRCALPHA)

        for row in range(rows):
            row_offset = row - (rows - 1) / 2
            normalized = 0.0 if rows == 1 else abs(row_offset) / ((rows - 1) / 2)
            row_columns = max(3, columns - round(normalized * 2))
            tilt_shift = round(math.tan(rotation) * row_offset * pitch)
            for column in range(row_columns):
                column_offset = column - (row_columns - 1) / 2
                x = round(center[0] + column_offset * pitch + tilt_shift)
                y = round(center[1] + row_offset * pitch)
                glow_rect = pygame.Rect(x - 5, y - 5, 10, 10)
                pygame.draw.rect(glow, (*color[:3], 35), glow_rect)
                pixel = pygame.Rect(x - cell // 2, y - cell // 2, cell, cell)
                pygame.draw.rect(surface, color, pixel)
                core = pygame.Rect(x - 1, y - 1, 3, 3)
                pygame.draw.rect(surface, PHOSPHOR_CORE, core)

        surface.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    @staticmethod
    def _draw_mouth(
        surface: pygame.Surface,
        pose: FacePose,
        color: pygame.Color,
    ) -> None:
        center_x = 120
        center_y = 141 + round(pose.face_y_offset)
        width = round(28 * pose.mouth_width_scale)

        paths: list[list[tuple[int, int]]] = []
        if pose.mouth_shape is MouthShape.NEUTRAL:
            paths = [[(center_x - width // 2, center_y), (center_x + width // 2, center_y)]]
        elif pose.mouth_shape is MouthShape.SMILE:
            paths = [[
                (center_x - width // 2, center_y - 3),
                (center_x - width // 4, center_y + 5),
                (center_x, center_y + 8),
                (center_x + width // 4, center_y + 5),
                (center_x + width // 2, center_y - 3),
            ]]
        elif pose.mouth_shape is MouthShape.OPEN:
            height = 6 + round(15 * pose.mouth_openness)
            rect = pygame.Rect(0, 0, width, height)
            rect.center = (center_x, center_y)
            FaceRenderer._draw_glowing_rect(surface, rect, color)
            return
        elif pose.mouth_shape is MouthShape.SURPRISED:
            rect = pygame.Rect(0, 0, 14, 19)
            rect.center = (center_x, center_y)
            FaceRenderer._draw_glowing_rect(surface, rect, color)
            return
        elif pose.mouth_shape is MouthShape.THINKING:
            paths = [[(center_x - 2, center_y + 2), (center_x + 13, center_y - 2)]]
            pygame.draw.rect(surface, color, pygame.Rect(center_x - 13, center_y, 4, 4))
        elif pose.mouth_shape is MouthShape.SLEEPING:
            paths = [[(center_x - width // 2, center_y), (center_x, center_y - 2), (center_x + width // 2, center_y)]]
        elif pose.mouth_shape is MouthShape.WORRIED:
            paths = [[(center_x - width // 2, center_y + 5), (center_x, center_y - 5), (center_x + width // 2, center_y + 5)]]
        elif pose.mouth_shape is MouthShape.ERROR:
            paths = [[
                (center_x - 18, center_y),
                (center_x - 9, center_y - 5),
                (center_x, center_y + 5),
                (center_x + 9, center_y - 5),
                (center_x + 18, center_y),
            ]]

        for path in paths:
            FaceRenderer._draw_glowing_path(surface, path, color)

    @staticmethod
    def _draw_glowing_path(
        surface: pygame.Surface,
        points: list[tuple[int, int]],
        color: pygame.Color,
    ) -> None:
        glow = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.lines(glow, (*color[:3], 55), False, points, 8)
        surface.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.lines(surface, color, False, points, 4)

    @staticmethod
    def _draw_glowing_rect(
        surface: pygame.Surface,
        rect: pygame.Rect,
        color: pygame.Color,
    ) -> None:
        glow = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        pygame.draw.rect(glow, (*color[:3], 50), rect.inflate(7, 7), 5)
        surface.blit(glow, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        pygame.draw.rect(surface, color, rect, 4)

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
        if face.expression is Expression.LISTENING:
            end_angle = math.radians(70 + 25 * abs(math.sin(elapsed * 4)))
            pygame.draw.arc(surface, INDICATOR_COLOR, pygame.Rect(13, 13, 214, 214), math.radians(45), end_angle, 3)
        elif face.expression is Expression.THINKING:
            active = int(elapsed * 3) % 3
            for index, x in enumerate((108, 120, 132)):
                pygame.draw.rect(surface, INDICATOR_COLOR, pygame.Rect(x - 2, 24, 4, 4 if index == active else 2))
        elif face.expression is Expression.SPEAKING and not buddy_text:
            for index, x in enumerate((111, 120, 129)):
                height = 5 + round(7 * abs(math.sin(elapsed * 7 + index)))
                pygame.draw.rect(surface, INDICATOR_COLOR, pygame.Rect(x - 2, 26 - height // 2, 4, height))
        elif face.expression is Expression.TIMER:
            timer = self._small_font.render(timer_text, True, INDICATOR_COLOR)
            surface.blit(timer, timer.get_rect(center=(120, 27)))
            if timer_status_text:
                paused = self._tiny_font.render(timer_status_text, True, INDICATOR_COLOR)
                surface.blit(paused, paused.get_rect(center=(120, 42)))
        elif face.expression is Expression.SURPRISED:
            self._draw_centered_message(surface, notification_text or "!")
        elif face.expression is Expression.SLEEPING:
            marker = self._small_font.render("z Z", True, PHOSPHOR)
            surface.blit(marker, marker.get_rect(center=(178, 54)))
        elif face.expression is Expression.ERROR:
            marker = self._small_font.render("! ERROR", True, ERROR_COLOR)
            surface.blit(marker, marker.get_rect(center=(120, 27)))

    def _draw_centered_message(self, surface: pygame.Surface, text: str) -> None:
        lines = self._wrap_text(text, max_width=160, max_lines=2)
        for index, line in enumerate(lines):
            rendered = self._small_font.render(line, True, INDICATOR_COLOR)
            surface.blit(rendered, rendered.get_rect(center=(120, 24 + index * 14)))

    def _draw_connection_arc(self, surface: pygame.Surface, status: str) -> None:
        color = CONNECTED_COLOR if status == "CONNECTED" else ERROR_COLOR
        pygame.draw.arc(
            surface,
            color,
            pygame.Rect(8, 8, 224, 224),
            math.radians(218),
            math.radians(252),
            3,
        )

    def _draw_text_input(self, surface: pygame.Surface, label: str, text: str) -> None:
        panel = pygame.Rect(26, 157, 188, 48)
        pygame.draw.rect(surface, pygame.Color("#09242A"), panel)
        pygame.draw.rect(surface, STATUS_COLOR, panel, 1)
        prompt = self._tiny_font.render(f"{label} >", True, INDICATOR_COLOR)
        surface.blit(prompt, (34, 166))
        available = 166 - prompt.get_width()
        value_text = self._fit_text(text or "Type message...", available)
        value = self._tiny_font.render(value_text, True, PHOSPHOR)
        surface.blit(value, (38 + prompt.get_width(), 166))
        help_text = self._tiny_font.render("ENTER SEND   ESC CANCEL", True, STATUS_COLOR)
        surface.blit(help_text, help_text.get_rect(center=(120, 190)))

    def _draw_help(self, surface: pygame.Surface) -> None:
        pygame.draw.circle(surface, pygame.Color("#020B0F"), self._center, self._radius - 3)
        title = self._small_font.render("SIMULATOR CONTROLS", True, INDICATOR_COLOR)
        surface.blit(title, title.get_rect(center=(120, 24)))

        sections = [
            (35, 49, "EVENTS", ["F BUTTON", "P PRESENCE", "T TALK", "N NOTIFY"]),
            (126, 49, "STATES", ["1 IDLE  2 LISTEN", "3 THINK 4 SPEAK", "5 TIMER 6 NOTIFY", "7 SLEEP 8 ERROR"]),
            (35, 123, "TIMER", ["UP/DN SET", "ENTER START", "SPACE PAUSE", "C CANCEL"]),
            (126, 123, "FACE", ["WASD LOOK", "X CENTER", "B BLINK", "H HAPPY"]),
        ]
        for x, y, heading, lines in sections:
            heading_surface = self._tiny_font.render(heading, True, PHOSPHOR)
            surface.blit(heading_surface, (x, y))
            for index, line in enumerate(lines):
                item = self._tiny_font.render(line, True, STATUS_COLOR)
                surface.blit(item, (x, y + 14 + index * 13))

        footer = self._tiny_font.render("? / F1 CLOSE     ESC QUIT", True, STATUS_COLOR)
        surface.blit(footer, footer.get_rect(center=(120, 211)))

    def _draw_scanlines(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        center_x, center_y = self._center
        for y in range(center_y - self._radius + 4, center_y + self._radius, 4):
            distance = y - center_y
            half_width = math.sqrt(max(0, self._radius**2 - distance**2))
            pygame.draw.line(
                overlay,
                (0, 0, 0, 34),
                (round(center_x - half_width), y),
                (round(center_x + half_width), y),
            )
        surface.blit(overlay, (0, 0))

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
            if self._small_font.size(candidate)[0] <= max_width:
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
        if self._tiny_font.size(text)[0] <= max_width:
            return text
        shortened = text
        while shortened and self._tiny_font.size(f"{shortened}…")[0] > max_width:
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
    scaled = pygame.transform.scale(virtual_display, scaled_size)
    destination = scaled.get_rect(center=window.get_rect().center)
    window.fill(pygame.Color("black"))
    window.blit(scaled, destination)
