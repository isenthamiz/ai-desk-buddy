"""Desktop simulator application loop."""

import argparse
import logging

import pygame

from aideskbuddy_simulator.config import DisplayConfig
from aideskbuddy_simulator.controller import SimulatorController
from aideskbuddy_simulator.core.state import DeskBuddyState
from aideskbuddy_simulator.face.controller import Expression, LookDirection
from aideskbuddy_simulator.features.timer import TimerStatus
from aideskbuddy_simulator.renderer import FaceRenderer, scale_to_window
from aideskbuddy_simulator.transport import DeviceClient

LOGGER = logging.getLogger(__name__)

KEY_STATE_MAP = {
    pygame.K_1: DeskBuddyState.IDLE,
    pygame.K_2: DeskBuddyState.LISTENING,
    pygame.K_3: DeskBuddyState.THINKING,
    pygame.K_4: DeskBuddyState.SPEAKING,
    pygame.K_5: DeskBuddyState.TIMER,
    pygame.K_6: DeskBuddyState.NOTIFICATION,
    pygame.K_7: DeskBuddyState.SLEEPING,
    pygame.K_8: DeskBuddyState.ERROR,
}


def handle_key(controller: SimulatorController, key: int) -> None:
    """Translate local developer controls into simulator actions."""
    if key in KEY_STATE_MAP:
        controller.select_state(KEY_STATE_MAP[key])
    elif key == pygame.K_UP:
        controller.adjust_timer(10)
    elif key == pygame.K_DOWN:
        controller.adjust_timer(-10)
    elif key == pygame.K_RETURN:
        controller.start_timer()
    elif key == pygame.K_SPACE:
        if controller.timer.status is TimerStatus.RUNNING:
            controller.pause_timer()
        else:
            controller.resume_timer()
    elif key == pygame.K_c:
        controller.cancel_timer()
    elif key == pygame.K_b:
        controller.blink()
    elif key == pygame.K_h:
        controller.set_face_expression(Expression.HAPPY)
    elif key == pygame.K_a:
        controller.look_at(LookDirection.LEFT)
    elif key == pygame.K_d:
        controller.look_at(LookDirection.RIGHT)
    elif key == pygame.K_w:
        controller.look_at(LookDirection.UP)
    elif key == pygame.K_s:
        controller.look_at(LookDirection.DOWN)
    elif key == pygame.K_x:
        controller.look_at(LookDirection.CENTER)


def send_device_event(
    client: DeviceClient,
    controller: SimulatorController,
    message: dict[str, object],
) -> bool:
    """Send a public protocol event or show local connection feedback."""
    if client.send(message):
        LOGGER.info("Device -> Server: %s", message)
        return True
    controller.show_notification("Server not connected", duration_seconds=1.5)
    return False


def run(
    *,
    initial_state: DeskBuddyState = DeskBuddyState.IDLE,
    timer_duration_seconds: float = 60.0,
    notification_duration_seconds: float = 2.5,
    server_url: str = "ws://127.0.0.1:8000/ws/device",
    device_id: str = "simulator-001",
    connect_to_server: bool = True,
    max_frames: int | None = None,
) -> None:
    """Run the simulator; ``max_frames`` supports bounded smoke tests."""
    config = DisplayConfig()
    controller = SimulatorController(
        initial_state=initial_state,
        timer_duration_seconds=timer_duration_seconds,
        notification_duration_seconds=notification_duration_seconds,
    )
    client = DeviceClient(server_url, device_id=device_id)
    if connect_to_server:
        client.start()

    pygame.init()
    try:
        window = pygame.display.set_mode(config.window_size, pygame.RESIZABLE)
        virtual_display = pygame.Surface(
            (config.virtual_width, config.virtual_height)
        ).convert()
        renderer = FaceRenderer(config)
        clock = pygame.time.Clock()
        running = True
        frames = 0
        input_mode: str | None = None
        input_text = ""
        presence_detected = False
        show_help = False

        while running:
            delta_seconds = clock.tick(config.frames_per_second) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.TEXTINPUT and input_mode is not None:
                    input_text = (input_text + event.text)[:100]
                elif event.type == pygame.KEYDOWN:
                    if input_mode is not None:
                        if event.key == pygame.K_ESCAPE:
                            input_mode = None
                            input_text = ""
                            pygame.key.stop_text_input()
                        elif event.key == pygame.K_BACKSPACE:
                            input_text = input_text[:-1]
                        elif event.key == pygame.K_RETURN:
                            message_text = input_text.strip()
                            if message_text:
                                if input_mode == "NOTIFY":
                                    controller.show_notification(message_text)
                                else:
                                    send_device_event(
                                        client,
                                        controller,
                                        {"type": "USER_TEXT", "text": message_text},
                                    )
                                input_mode = None
                                input_text = ""
                                pygame.key.stop_text_input()
                    elif event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_F1 or event.unicode == "?":
                        show_help = not show_help
                    elif event.key in {pygame.K_n, pygame.K_t}:
                        input_mode = "NOTIFY" if event.key == pygame.K_n else "TALK"
                        input_text = ""
                        pygame.key.start_text_input()
                    elif event.key == pygame.K_f:
                        send_device_event(
                            client,
                            controller,
                            {"type": "BUTTON_PRESSED", "button": "ACTION"},
                        )
                    elif event.key == pygame.K_p:
                        next_presence = not presence_detected
                        if send_device_event(
                            client,
                            controller,
                            {
                                "type": "PRESENCE_CHANGED",
                                "present": next_presence,
                            },
                        ):
                            presence_detected = next_presence
                    else:
                        handle_key(controller, event.key)

            for message in client.receive_pending():
                LOGGER.info("Server -> Device: %s", message)
                controller.handle_server_message(message)

            controller.update(delta_seconds)
            pygame.display.set_caption(
                f"AI Desk Buddy Simulator — {controller.state.value}"
            )
            connection_status = (
                client.status.value if connect_to_server else "OFFLINE"
            )
            renderer.render(
                virtual_display,
                controller.face,
                controller.state,
                timer_text=controller.timer_text,
                timer_status_text=controller.timer_status_text,
                notification_text=controller.notification_text,
                buddy_text=controller.buddy_text,
                connection_status=connection_status,
                debug_input_label=input_mode,
                debug_input_text=input_text,
                show_help=show_help,
            )
            scale_to_window(virtual_display, window)
            pygame.display.flip()

            frames += 1
            if max_frames is not None and frames >= max_frames:
                running = False
    finally:
        pygame.key.stop_text_input()
        pygame.quit()
        client.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AI Desk Buddy simulator")
    parser.add_argument(
        "--state",
        type=lambda value: DeskBuddyState(value.upper()),
        choices=list(DeskBuddyState),
        default=DeskBuddyState.IDLE,
        help="initial Desk Buddy state (default: IDLE)",
    )
    parser.add_argument(
        "--timer-duration",
        type=float,
        default=60.0,
        metavar="SECONDS",
        help="initial timer duration in seconds (default: 60)",
    )
    parser.add_argument(
        "--notification-duration",
        type=float,
        default=2.5,
        metavar="SECONDS",
        help="notification display duration in seconds (default: 2.5)",
    )
    parser.add_argument(
        "--server-url",
        default="ws://127.0.0.1:8000/ws/device",
        help="device WebSocket URL",
    )
    parser.add_argument("--device-id", default="simulator-001")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="disable the server connection and use local preview controls only",
    )
    args = parser.parse_args()
    if args.timer_duration <= 0:
        parser.error("--timer-duration must be greater than zero")
    if args.notification_duration <= 0:
        parser.error("--notification-duration must be greater than zero")

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    run(
        initial_state=args.state,
        timer_duration_seconds=args.timer_duration,
        notification_duration_seconds=args.notification_duration,
        server_url=args.server_url,
        device_id=args.device_id,
        connect_to_server=not args.offline,
    )


if __name__ == "__main__":
    main()
