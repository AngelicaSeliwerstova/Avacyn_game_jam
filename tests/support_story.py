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


def read_document(session, choice=0):
    assert session.dialog.presentation == "document"
    for _ in range(40):
        actions = {b.action for b in session.dialog.buttons}
        if "document_next" in actions:
            assert session.handle_action("document_next")
        else:
            assert session.handle_action("document_close")
            finish_conversation(session, choice)
            return
    raise AssertionError("Document did not finish")


def complete_patient_archive(session, choice=0):
    session._files.show()
    for action in ("files_year:1981", "files_case", "files_letter"):
        assert session.handle_action(action), action
    read_document(session, choice)
    assert session.handle_action("files_close")
    finish_conversation(session, choice)


def finish_office(session):
    finish_conversation(session)
    assert session._document_id == "office_case"
    read_document(session)
    assert session.dialog.presentation == "interference"
    session.tick_presentation(1.8)
    assert session.dialog.presentation == "blackout"
    session.tick_presentation(2.2)


def finish_memory(session):
    """Advance real presentation and world time, including automatic voices and pauses."""
    for _ in range(1600):
        if session.dialog is not None and session.dialog.presentation == "ending":
            return
        session.tick_presentation(.1)
        session.update(.1)
    raise AssertionError("Memory did not reach ending")
