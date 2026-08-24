"""Bounded application-loop smoke test."""

import pytest

import pygame

from aideskbuddy_simulator.app import KEY_STATE_MAP, handle_key, run
from aideskbuddy_simulator.config import DisplayConfig
from aideskbuddy_simulator.controller import EXPRESSION_FOR_STATE, SimulatorController
from aideskbuddy_simulator.core.state import DeskBuddyState
from aideskbuddy_simulator.face.controller import Expression, LookDirection
from aideskbuddy_simulator.renderer import FaceRenderer


@pytest.mark.parametrize("state", list(DeskBuddyState))
def test_application_renders_every_state_for_one_frame(monkeypatch, state) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")

    run(initial_state=state, connect_to_server=False, max_frames=1)


def test_every_state_has_a_face_expression() -> None:
    assert set(EXPRESSION_FOR_STATE) == set(DeskBuddyState)


def test_every_state_has_a_keyboard_shortcut() -> None:
    assert set(KEY_STATE_MAP.values()) == set(DeskBuddyState)


def test_face_debug_keys_use_face_controller_api() -> None:
    controller = SimulatorController()

    handle_key(controller, pygame.K_a)
    assert controller.face.look_direction is LookDirection.LEFT

    handle_key(controller, pygame.K_h)
    assert controller.face.expression is Expression.HAPPY

    handle_key(controller, pygame.K_b)
    assert controller.face.is_blinking


def test_command_help_overlay_renders(monkeypatch) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    try:
        config = DisplayConfig()
        surface = pygame.Surface((config.virtual_width, config.virtual_height))
        controller = SimulatorController()

        FaceRenderer(config).render(
            surface,
            controller.face,
            controller.state,
            show_help=True,
        )
    finally:
        pygame.quit()
