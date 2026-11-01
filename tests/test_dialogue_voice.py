from array import array
import math
import unittest
from unittest.mock import Mock, patch

import pygame

from config import settings
from game.campaign import Campaign
from game.dialogue_voice import DialogueTyper, DialogueVoice, DialogueVoiceProfile, synthesize_blip


class DialogueVoiceTests(unittest.TestCase):
    def session(self):
        session = Campaign().load_level("start").session
        session._voice = Mock()
        return session

    def test_spoken_text_reveals_with_voice_and_first_press_skips_only_the_animation(self):
        session = self.session()
        original = session.dialog.message
        self.assertEqual(session.dialog.visible_characters, 0)
        session.tick_presentation(0.1)
        self.assertGreater(session.dialog.visible_characters, 0)
        self.assertLess(session.dialog.visible_characters, len(original))
        session._voice.play.assert_called()
        self.assertTrue(session.handle_action("story_next"))
        self.assertEqual(session.dialog.message, original)
        self.assertEqual(session.dialog.visible_characters, len(original))
        session._voice.stop.assert_called()
        session.handle_action("story_next")
        self.assertNotEqual(session.dialog.message, original)
        self.assertEqual(session.dialog.visible_characters, 0)

    def test_heroine_and_doctor_use_their_external_voice_profiles(self):
        session = self.session()
        session.tick_presentation(0.1)
        first = session._voice.play.call_args.args[0]
        self.assertEqual(first.pitch_hz, session.book.data["characters"]["hero"]["voice"]["pitch_hz"])
        while session._node['speaker'] != 'doctor':
            session.reveal_dialogue()
            session.handle_action("story_next")
        session.tick_presentation(0.1)
        second = session._voice.play.call_args.args[0]
        self.assertEqual(second.pitch_hz, session.book.data["characters"]["doctor"]["voice"]["pitch_hz"])
        self.assertNotEqual(first.pitch_hz, second.pitch_hz)

    def test_finished_line_choices_and_documents_are_silent(self):
        session = self.session()
        for _ in range(500):
            session.tick_presentation(0.05)
        calls = session._voice.play.call_count
        self.assertGreater(calls, 0)
        for _ in range(30):
            session.tick_presentation(0.1)
        self.assertEqual(session._voice.play.call_count, calls)
        session._queue.clear()
        session._prepend(session.act,[{'type':'dialogue','id':'after_letter'}])
        session._advance()
        for _ in range(30):
            if any(button.action.startswith("story_choice:") for button in session.dialog.buttons):
                break
            session.reveal_dialogue()
            session.handle_action("story_next")
        self.assertIsNone(session.dialog.visible_characters)
        session._voice.reset_mock()
        session.tick_presentation(1)
        session._voice.play.assert_not_called()
        session.open_document("mother_letter")
        session.tick_presentation(1)
        session._voice.play.assert_not_called()

    def test_global_mute_keeps_typing_and_cleanup_stops_the_voice(self):
        session = self.session()
        for option in ("AUDIO_ENABLED", "DIALOGUE_BEEPS_ENABLED"):
            with patch.object(settings, option, False):
                session._voice.reset_mock()
                before = session.dialog.visible_characters
                session.tick_presentation(0.1)
                self.assertGreater(session.dialog.visible_characters, before)
                session._voice.play.assert_not_called()
                session._voice.stop.assert_called()
        session.release()
        session._voice.release.assert_called_once()

    def test_punctuation_delays_typing_and_slow_frames_never_queue_a_burst(self):
        typer = DialogueTyper("А, б", DialogueVoiceProfile(chars_per_second=40))
        self.assertIsNone(typer.update(0.04))
        self.assertEqual(typer.visible, 2)
        self.assertIsNone(typer.update(0.05))
        self.assertEqual(typer.visible, 2)
        slow = DialogueTyper("Реплика " * 100, DialogueVoiceProfile())
        cue = slow.update(10)
        self.assertIsInstance(cue, tuple)
        self.assertLess(slow.visible, 15)
        whitespace = DialogueTyper(" ,… !", DialogueVoiceProfile())
        for _ in range(100):
            self.assertIsNone(whitespace.update(0.1))

    def test_generated_blips_have_soft_edges_and_distinct_character_tones(self):
        first = synthesize_blip(820, 44100, 1)
        second = synthesize_blip(560, 44100, 1)
        self.assertNotEqual(first, second)
        samples = array("h", first)
        self.assertEqual(len(samples), round(0.04 * 44100))
        self.assertEqual(samples[0], 0)
        self.assertEqual(samples[-1], 0)
        self.assertLessEqual(max(abs(sample) for sample in samples), 32767 * 0.28)
        self.assertGreater(math.sqrt(sum(sample * sample for sample in samples) / len(samples)), 1000)
        self.assertEqual(len(synthesize_blip(820, 44100, 2)), len(first) * 2)

    def test_invalid_profiles_are_rejected_and_an_actor_can_be_silent(self):
        self.assertFalse(DialogueVoiceProfile.from_data(False).enabled)
        for data in ({"pitch_hz": -1}, {"volume": 2}, {"chars_per_second": 0},
                     {"pitch_variation": float("nan")}, {"typo": 1}, "voice"):
            with self.subTest(data=data), self.assertRaises(ValueError):
                DialogueVoiceProfile.from_data(data)

    def test_missing_sound_device_does_not_interrupt_the_conversation(self):
        voice = DialogueVoice()
        with patch("pygame.get_init", return_value=True), patch("pygame.mixer.get_init", return_value=None), \
                patch("pygame.mixer.init", side_effect=pygame.error("no device")):
            voice.play(DialogueVoiceProfile(), "а", 0)
            voice.stop()
            voice.release()


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


if __name__ == "__main__":
    unittest.main()
