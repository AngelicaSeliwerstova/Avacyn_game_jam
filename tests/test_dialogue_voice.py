"""Dialogue keeps its typing and progression without synthesized audio."""
import unittest
from unittest.mock import Mock, patch

from config import settings
from game.campaign import Campaign
from game.dialogue_voice import DialogueTyper, DialogueVoiceProfile


class SilentDialogueTests(unittest.TestCase):
    def session(self):
        session = Campaign().load_level('start').session
        self.addCleanup(session.release)
        return session

    def test_typing_and_first_press_reveal_work_without_generating_sound(self):
        with patch.object(settings, 'AUDIO_ENABLED', True), patch('pygame.mixer.Sound') as sound:
            session = self.session()
            original = session.dialog.message
            self.assertEqual(session.dialog.visible_characters, 0)
            session.tick_presentation(.1)
            self.assertGreater(session.dialog.visible_characters, 0)
            self.assertLess(session.dialog.visible_characters, len(original))
            self.assertTrue(session.handle_action('story_next'))
            self.assertEqual(session.dialog.visible_characters, len(original))
            session.handle_action('story_next')
            self.assertNotEqual(session.dialog.message, original)
            sound.assert_not_called()

    def test_finished_lines_choices_and_documents_remain_silent(self):
        with patch.object(settings, 'AUDIO_ENABLED', True), patch('pygame.mixer.Sound') as sound:
            session = self.session()
            for _ in range(500):
                session.tick_presentation(.05)
            self.assertEqual(session.dialog.visible_characters, len(session.dialog.message))
            session.open_document('mother_letter')
            session.tick_presentation(1)
            sound.assert_not_called()

    def test_legacy_voice_flag_cannot_enable_speech_in_memory(self):
        session = self.session()
        session._cue_sounds = Mock()
        session._cue_sounds._paths = {}
        session._queue.clear()
        session._prepend(session.act, [{'type': 'voiceover', 'id': 'cradle_memory', 'audio': True}])
        with patch.object(settings, 'AUDIO_ENABLED', True):
            session._advance()
            for _ in range(1000):
                session.tick_presentation(.25)
                if session.dialog is None:
                    break
        self.assertIsNone(session.dialog)
        session._cue_sounds.play_voice.assert_not_called()
        session._cue_sounds.play_discovery.assert_not_called()

    def test_punctuation_pauses_and_slow_frame_limit_are_preserved(self):
        typer = DialogueTyper('А, б', DialogueVoiceProfile(chars_per_second=40))
        self.assertIsNone(typer.update(.04))
        self.assertEqual(typer.visible, 2)
        typer.update(.05)
        self.assertEqual(typer.visible, 2)
        slow = DialogueTyper('Реплика ' * 100, DialogueVoiceProfile())
        self.assertIsNone(slow.update(10))
        self.assertLess(slow.visible, 15)

    def test_legacy_profile_validation_still_accepts_text_timing(self):
        for data in ({'pitch_hz': -1}, {'volume': 2}, {'chars_per_second': 0},
                     {'pitch_variation': float('nan')}, {'typo': 1}, 'voice'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                DialogueVoiceProfile.from_data(data)
