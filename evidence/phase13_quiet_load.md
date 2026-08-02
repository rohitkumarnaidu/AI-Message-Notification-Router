# Phase 13 Quiet Hours and Notification Load

- Implementation: `quiet_load.py` evaluates load and quiet hours.
- Identifies if message was received during quiet hours (22:00 to 08:00 by default).
- Prevents non-urgent notifications during quiet hours, downgrading them to digest.
- Calculates notification load based on user history and throttles excessive non-urgent volume.
