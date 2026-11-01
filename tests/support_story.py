def finish_conversation(session, choice=0):
    """Read spoken lines and choose one response; stop at documents or effects."""
    for _ in range(80):
        if session.dialog is None or session.dialog.presentation not in ("conversation", "memory"):
            return
        session.reveal_dialogue()
        actions = [button.action for button in session.dialog.buttons]
        action = f"story_choice:{choice}" if any(a.startswith("story_choice:") for a in actions) else actions[0]
        assert session.handle_action(action), action
    raise AssertionError("Conversation did not finish")
