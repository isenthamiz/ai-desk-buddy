# AI Desk Buddy Features

This document captures the currently selected product areas. It is a roadmap, not a commitment to implement every feature in the first version.

For the inventory of capabilities that already exist, see
[`implemented-features.md`](implemented-features.md).

## Selected feature areas

1. **Personality & Animated Face**
   - expressive idle/listening/thinking/speaking states
   - simple personality appropriate for short spoken interactions

2. **Voice Assistant**
   - voice input and spoken responses
   - start with push-to-talk; wake word can come later

3. **Timer & Focus Mode**
   - create/cancel timers
   - countdown display
   - audible/visual completion
   - focus/Pomodoro-style behavior later

4. **Calendar & Meetings**
   - show upcoming meetings
   - meeting awareness/alerts
   - integration details to be designed later

5. **Computer Notifications**
   - surface useful computer notifications on the buddy
   - exact desktop integration is not yet designed

6. **Developer Mode**
   - developer-oriented status/actions
   - exact integrations and commands are not yet finalized

7. **AI Agent / Tools**
   - structured tools for deterministic actions
   - extend integrations incrementally
   - initial Todoist integration creates, lists, and completes tasks

8. **Quick Notes / Ideas**
   - capture short notes/ideas through the buddy
   - storage/integration target to be decided later

9. **Reminders**
   - create and surface reminders
   - persistence required once implemented

10. **Presence Detection**
    - wake/react when someone is at the desk
    - sleep/dim after inactivity

11. **Touch Interaction**
    - touch-based reactions/actions depending on final hardware

12. **Physical Controls**
    - buttons and/or rotary controls
    - examples: push-to-talk, volume, dismiss/cancel

13. **Sounds & Voice**
    - notification sounds
    - speech playback
    - audio feedback for interactions

14. **Desk Dashboard**
    - lightweight daily information/status
    - weather/environment information is not intended to be central
    - initial weather reporting supports current, today, and tomorrow conditions
      for one backend-configured location

15. **Morning Briefing**
    - concise start-of-day summary
    - sources/integrations to be designed later

16. **End-of-Day Mode**
    - end-of-day summary or shutdown-style routine
    - behavior to be designed later

17. **Fun / Easter Eggs**
    - playful animations, reactions, or hidden interactions

18. **Device Management**
    - connectivity/status
    - configuration
    - future OTA/update capabilities

## Explicitly out of scope for the current concept
- desk environmental sensing as a core feature
- smart-home integration

## Product principles
- The device should feel like a desk companion, not merely a voice API client.
- Spoken responses should normally be concise.
- Hardware should remain relatively simple; complex logic belongs in the backend.
- Features should be delivered incrementally and should not block basic device interaction.
