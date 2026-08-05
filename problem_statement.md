# System Specification & Data Schema

This document outlines the core requirements, input schemas, and expected outputs for the AI-powered Message Notification Router.

## Core Objective

The system must reason over **multimodal messages**, including text messages, image posters/screenshots, and voice notes. For every incoming WhatsApp message, the system must decide whether the user should be interrupted now, whether the message can be batched into a digest, or whether it should be muted.

The routing decision must be personalized to the receiving user. A sale poster may be useful for one user and unwanted noise for another. A payment reminder may be legitimate from a trusted admin but risky from a new sender. A muted family group can still contain an urgent direct mention. Clear scams or safety risks must be muted regardless of the user's usual engagement.

## Routing Actions

The system reviews each incoming message and categorizes it into one of three actions:

- `notify`: Important enough to interrupt now.
- `digest`: Useful, but can be shown later.
- `mute`: Low-value, repetitive, unwanted, suspicious, or unsafe.

## System Context & Datasets

The router utilizes multiple data sources to make contextual decisions (stored in `dataset/`):

1. **Messages (`messages.csv`)** - Incoming messages to route.
2. **Users (`users.csv`)** - Basic user notification behavior, quiet hours, and recent engagement metrics.
3. **Groups (`groups.csv`)** - Information about group chats (type, size, admins, activity).
4. **Group Members (`group_members.csv`)** - User-group relationships, role, activity, and mute state.
5. **Business Accounts (`business_accounts.csv`)** - Business sender metadata, verification, and domain trust.
6. **User-Business History (`user_business_history.csv`)** - Historical relationships (orders, bookings, opt-ins).
7. **Message History (`message_history.csv`)** - Past messages received by users to identify patterns or risks.
8. **Message Events (`message_events.csv`)** - How users reacted to past messages (opened, replied, muted).
9. **Media Files (`images.csv`, `voice_notes.csv`)** - Media metadata and local paths.

## Input Schema

Each incoming message contains the following fields:

- `message_id`: Unique incoming message ID
- `user_id`: User receiving the message
- `conversation_type`: `personal`, `group`, or `business`
- `group_id`: Group ID if the message is from a group
- `business_id`: Business ID if the message is from a business account
- `sender_user_id`: Sender user ID if the message is from a user
- `created_at`: Message timestamp
- `message_text`: Text content for text messages; empty for voice-note messages
- `media_type`: Empty, `image`, or `voice`
- `media_id`: Linked image or voice-note ID, if present
- `forwarded_count`: Forwarding signal

## Output Schema & Allowed Values

The system produces a unified prediction with the following structured output:

- `message_id`: The incoming message ID
- `action`: `notify`, `digest`, or `mute`
- `message_type`: Best-fit category:
  - `personal`, `urgent`, `event`, `payment`, `business_update`, `promotion`, `greeting`, `forward`, `spam`, `scam`, `unknown`
- `reason`: Short human-readable explanation for the decision
- `confidence`: Calibrated confidence score (`0.0` to `1.0`)
- `evidence_message_ids`: Semicolon-separated historical message IDs used as context (or `none`)
