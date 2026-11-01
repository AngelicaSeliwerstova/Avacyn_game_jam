"""Revised chapters connect the nursery, the archive and the final door."""
import unittest
from unittest.mock import patch
import glm
from config import settings
from engine.input.state import InputState
from game.campaign import Campaign
from game.levels.final_chapter import HELP_PLAYER
from support_story import finish_conversation, read_document
from test_hospital import make_body, walk


def advance_scene(session):
    for _ in range(2000):
        if session.next_level or session.puzzle_active:
            return
        if session.dialog:
            if session.dialog.presentation == 'ending':
                return
            if session.dialog.presentation in ('conversation', 'memory'):
                finish_conversation(session)
                continue
            if session.dialog.presentation == 'document':
                read_document(session)
                continue
        elif not (session.controls_locked or session._queue):
            return
        session.tick_presentation(.25)
        for obj in session.level.objects:
            obj.update(.25)
        session.update(.25)
    raise AssertionError('Scene did not finish')


class RevisedCampaignTests(unittest.TestCase):
    def setUp(self):
        mute = patch.object(settings, 'AUDIO_ENABLED', False)
        mute.start()
        self.addCleanup(mute.stop)

    def load(self, campaign, level):
        scene = campaign.load_level(level)
        self.addCleanup(scene.session.release)
        advance_scene(scene.session)
        return scene

    def interact(self, scene, name):
        obj = next(o for o in scene.level.objects if o.name == name)
        scene.player._interactions._activate(obj)
        scene.session.update(0)
        advance_scene(scene.session)
        return obj

    def test_archive_requires_search_and_recording_must_finish_before_final_act(self):
        campaign = Campaign()
        scene = self.load(campaign, 'act1')
        session = scene.session
        self.assertIn('Найти сторожку', scene.player.objective_status)
        self.assertFalse(scene.player.story_first_person)
        self.interact(scene, 'security_archive')
        self.assertFalse(session.puzzle_active)
        self.assertNotIn('act1:archive_opened', session._flags)
        scene.player.body._position = glm.vec3(-3, 0, 2.4)
        session.update(0)
        advance_scene(session)
        self.assertIn('act1:security_seen', session._flags)
        self.interact(scene, 'security_lost_items')
        self.assertIn('act1:lost_items_searched', session._flags)
        self.interact(scene, 'security_archive')
        self.assertTrue(session.puzzle_active)
        self.assertEqual(session._puzzle.progress.order, list('CADB'))
        for index, frame in enumerate('ABCD'):
            current = session._puzzle.progress.order.index(frame)
            if current != index:
                session.handle_puzzle_action(f'archive_swap:{index}:{current}')
        session.handle_puzzle_action('archive_check')
        self.assertNotIn('act1:complete', session._flags)
        session.handle_puzzle_action('archive_play')
        self.assertFalse(session.handle_puzzle_action('archive_frame:0'))
        session.handle_puzzle_action('archive_close')
        self.assertNotIn('archive_recording_watched', session._flags)
        self.interact(scene, 'security_archive')
        for _ in range(3000):
            session.tick_presentation(.25)
            if not session.puzzle_active:
                break
        else:
            self.fail('Recording never finished')
        session.update(0)
        advance_scene(session)
        self.assertEqual(session.dialog.title, 'КОНЕЦ АКТА 2')
        self.assertIn('act1:complete', session._flags)
        self.assertNotIn('incident_report_read', session._flags)
        self.assertTrue(session.handle_action('story_continue'))
        advance_scene(session)
        self.assertEqual(session.act.id, 'act2')
        self.assertIn('Вернуться к лестнице', scene.player.objective_status)
        self.assertFalse(scene.player.story_first_person)
        self.assertTrue(next(o for o in scene.level.objects if o.name == 'friend_body').boxes)

    def test_final_help_heals_world_and_only_closing_door_from_inside_ends_game(self):
        campaign = Campaign()
        scene = self.load(campaign, 'act2')
        session = scene.session
        self.assertFalse(scene.player.story_first_person)
        self.assertFalse(scene.player.inventory.has_key('ward_313'))
        self.interact(scene, 'doctor_help')
        self.assertNotIn('act2:help_accepted', session._flags)
        scene.player.body._position = glm.vec3(-10, 0, 10)
        session.update(0)
        advance_scene(session)
        self.assertTrue(scene.player.story_first_person)
        self.assertFalse(scene.player.fixed_camera_effect_active)
        self.assertLess(glm.distance(scene.player.body.position, glm.vec3(HELP_PLAYER)), 1e-5)
        self.assertTrue(session.actors['doctor'].offering_help)
        self.assertIn('Принять помощь', scene.player.objective_status)
        scene.player.update(0, InputState())
        self.assertEqual(scene.player._interactions.focused.name, 'doctor_help')
        scene.player.update(0, InputState(interact=True))
        session.update(0)
        advance_scene(session)
        self.assertEqual(session.next_level, 'healed')
        healed = self.load(campaign, 'healed')
        self.assertTrue(healed.player.story_first_person)
        self.assertTrue(healed.player.inventory.has_key('ward_313'))
        self.assertEqual(healed.level.visual_style, 'peaceful')
        self.assertFalse(healed.level.invisible_barriers)
        for name in ('friend_body', 'fallen_pendant', 'doctor_help'):
            self.assertFalse(next(o for o in healed.level.objects if o.name == name).boxes)
        session = healed.session
        door = next(o for o in healed.level.objects if o.name == 'f3_patient_ward_313')
        door.set_state('open')
        door.update(2)
        healed.player._interactions._activate(door)
        session.update(0)
        self.assertNotIn('act2:complete', session._flags)
        door.update(2)
        door.set_state('open')
        door.update(2)
        healed.player.body._position = glm.vec3(18, 9.6, 5)
        session.update(0)
        self.assertIn('act2:inside_ward', session._flags)
        self.assertNotIn('closed:f3_patient_ward_313', healed.player.story_events)
        self.assertNotIn('act2:complete', session._flags)
        healed.player._interactions._activate(door)
        session.update(0)
        self.assertTrue(session.controls_locked)
        self.assertNotIn('act2:complete', session._flags)
        advance_scene(session)
        self.assertEqual(door.state_name, 'default')
        self.assertFalse(door.transitioning)
        self.assertEqual(session.dialog.title, 'КОНЕЦ ИГРЫ')
        self.assertIn('act2:complete', session._flags)
        self.assertNotIn('story_continue', {b.action for b in session.dialog.buttons})

    def test_healed_ward_is_reachable_up_the_actual_stair_and_doorway(self):
        scene = self.load(Campaign(), 'healed')
        from game.levels.spiral import SpiralStair
        player = scene.player
        player.body = make_body(player.body.world, (-12.95, 0, 8.6))
        walk(self, player.body, SpiralStair().walking_path(), fps=20)
        walk(self, player.body, ((-12.2, 9.6, 6.9), (-8, 9.6, 6.9), (12, 9.6, 6.9), (14.5, 9.6, 5)), fps=20)
        door = self.interact(scene, 'f3_patient_ward_313')
        door.update(2)
        walk(self, player.body, ((18, 9.6, 5),), fps=20)
        scene.session.update(0)
        self.assertIn('act2:inside_ward', scene.session._flags)
