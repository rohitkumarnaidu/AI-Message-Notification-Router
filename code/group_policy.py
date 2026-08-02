def adjust_for_group_policy(
    is_group: bool,
    is_group_muted: bool,
    is_direct_mention: bool,
    is_group_admin: bool,
    current_action: str
) -> str:
    if not is_group:
        return current_action
        
    if is_group_muted:
        # If the group is muted, generally mute everything
        new_action = "mute"
        
        # Exception: Direct mention by an admin (and possibly standard mentions if policy dictates)
        if is_direct_mention and is_group_admin:
            # Let it notify
            new_action = "notify"
        elif is_direct_mention:
            # Maybe digest standard mentions in muted groups
            new_action = "digest"
            
        return new_action
        
    return current_action
