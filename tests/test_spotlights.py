import unittest
from unittest.mock import Mock, patch
import glm
from config import settings
from game.campaign import Campaign
from game.hospital_audio import HospitalAudioSystem
from game.companions import CompanionSystem
from game.levels.spiral import SpiralStair
from game.levels.under_spotlights import MEMORY_CAMERA, CRADLE_TARGET
from engine.input.state import InputState
from support_story import complete_patient_archive, finish_conversation
from test_hospital import walk, make_body


class SpotlightsTests(unittest.TestCase):
    def begin(self):
        campaign=Campaign()
        scene=campaign.load_level('start')
        self.addCleanup(scene.session.release)
        finish_conversation(scene.session)
        scene.session._flags.add('act0:reception')
        complete_patient_archive(scene.session)
        return campaign,scene

    @patch.object(settings,'AUDIO_ENABLED',False)
    def test_stairs_locked_nursery_and_cradle_are_physically_reachable(self):
        _,scene=self.begin()
        player,session=scene.player,scene.session
        stair=SpiralStair()
        player.body=make_body(player.body.world,(-13,0,8.6))
        path=stair.walking_path()[:stair.steps]
        self.assertTrue(any(all(lo<v<hi for lo,v,hi in zip(session.act.data['zones']['damaged_rail']['min'],p,
                              session.act.data['zones']['damaged_rail']['max'])) for p in path))
        walk(self,player.body,path,fps=20)
        walk(self,player.body,((-12.2,4.8,6.9),(-7,4.8,6.9),(-7,4.8,-7.5),(-16,4.8,-7.5)),fps=20)
        door=next(o for o in scene.level.objects if o.name=='f2_surgery_preop')
        # Find the actual interaction from the ordinary fixed-camera view.
        player._active_camera_zone=None
        player.update(0,InputState())
        self.assertEqual(player._interactions.focused.name,door.name)
        self.assertIn('Использовать ключ',player.aim_text)
        player.update(0,InputState(interact=True))
        session.update(0)
        self.assertIn('act0:cry_stopped',session._flags)
        self.assertIsNone(session.dialog)
        door.update(1)
        walk(self,player.body,((-16,4.8,-12),(-16,4.8,-18.7)),fps=20)
        player._active_camera_zone=None
        player.update(0,InputState())
        self.assertEqual(player._interactions.focused.name,'f2_nursery_cradle')
        player.update(0,InputState(interact=True))
        session.update(0)
        self.assertEqual(session.dialog.presentation,'distortion')
        player._sync_fixed_camera()
        self.assertLess(glm.distance(player.camera.position,glm.vec3(MEMORY_CAMERA)),1e-5)
        self.assertLess(glm.distance(player.camera.target,glm.vec3(CRADLE_TARGET)),1e-5)

    @patch.object(settings,'AUDIO_ENABLED',False)
    def test_nail_only_sounds_and_subtitles_once_without_new_objective_or_dialogue(self):
        _,scene=self.begin()
        session=scene.session
        objective=scene.player.objective_status
        for _ in range(2):
            scene.player.body._position=glm.vec3(-10.2,1,3.3)
            session.update(0)
            self.assertIsNone(session.dialog)
            self.assertEqual(scene.player.objective_status,objective)
        self.assertIn('act0:scratched',session._flags)
        self.assertIn('Поцарапалась',scene.player.story_status)
        self.assertNotIn('Доктор',scene.player.story_status)
        session.update(10)
        self.assertEqual(scene.player.story_status,'')

    @patch.object(settings,'AUDIO_ENABLED',True)
    def test_cry_gets_louder_upstairs_and_stops_on_the_unlock_frame(self):
        with patch.object(settings,'AUDIO_ENABLED',False):
            _,scene=self.begin()
        sounds=Mock()
        system=HospitalAudioSystem(scene.level,scene.player,scene.session,sounds=sounds)
        scene.player.body._position=glm.vec3(10.5,0,3)
        system.update(0)
        cry=lambda: [c.args for c in sounds.loop.call_args_list if c.args[1]=='story:act0:crying_child'][-1]
        distant=max(cry()[-2:])
        scene.player.body._position=glm.vec3(-16,4.8,-8)
        system.update(0)
        self.assertGreater(max(cry()[-2:]),distant*4)
        sounds.reset_mock()
        door=next(o for o in scene.level.objects if o.name=='f2_surgery_preop')
        with patch.object(settings,'AUDIO_ENABLED',False):
            scene.player._interactions._activate(door)
            scene.session.update(0)
        system.set_paused(False)
        self.assertFalse(any(c.args[1]=='story:act0:crying_child' for c in sounds.loop.call_args_list))
        sounds.stop_loop.assert_any_call(4)

    @patch.object(settings,'AUDIO_ENABLED',False)
    def test_reloaded_key_stays_in_inventory_and_folder_does_not_return(self):
        campaign,scene=self.begin()
        restored=campaign.load_level('start')
        self.addCleanup(restored.session.release)
        self.assertTrue(restored.player.inventory.has_key('second_floor_key'))
        folder=next(o for o in restored.level.objects if o.name=='archive_case_081')
        self.assertEqual(folder.state_name,'removed')

    @patch.object(settings,'AUDIO_ENABLED',False)
    def test_doctor_can_follow_upstairs_into_the_new_cradle_room(self):
        _,scene=self.begin()
        system=next(s for s in scene.systems if isinstance(s,CompanionSystem))
        doctor=system.companions[0]
        doctor.body=make_body(doctor.body.world,(-13,0,8.6))
        door=next(o for o in scene.level.objects if o.name=='f2_surgery_preop')
        door.set_state('open')
        door.update(1)
        for goal in ((-7,4.8,6.9),(-16,4.8,-18.7)):
            scene.player.body=make_body(scene.player.body.world,goal)
            for _ in range(1400):
                system.update(1/30)
                if glm.distance(doctor.body.position,glm.vec3(goal))<1.6:
                    break
            else:
                self.fail(f'Doctor cannot reach nursery: {tuple(doctor.body.position)}; goal={goal}')
        self.assertAlmostEqual(doctor.body.position.y,4.8,places=3)

    @patch.object(settings,'AUDIO_ENABLED',False)
    def test_voice_pages_do_not_replay_recordings_and_mute_keeps_automatic_timing(self):
        _,scene=self.begin()
        session=scene.session
        bank=Mock()
        bank._paths={}
        session._cue_sounds=bank
        session._queue.clear()
        session._prepend(session.act,[{'type':'voiceover','id':'cradle_memory'}])
        with patch.object(settings,'AUDIO_ENABLED',True):
            session._advance()
            self.assertEqual(bank.play_voice.call_count,1)
            # First recorded line needs two subtitle pages; turning a page must
            # leave the recording playing on its own channel.
            first_page_time=session._voice_remaining
            session.tick_presentation(first_page_time)
            self.assertEqual(bank.play_voice.call_count,1)
            self.assertEqual(session.dialog.presentation,'voiceover')
            for _ in range(900):
                session.tick_presentation(.1)
                if session.dialog is None:
                    break
            self.assertEqual([c.args[0] for c in bank.play_voice.call_args_list],
                             [line['audio'] for line in session.act.dialogues['cradle_memory']])
        session._prepend(session.act,[{'type':'voiceover','id':'memory_outro_first'}])
        session._advance()
        session.tick_presentation(.1)
        bank.stop_effects.assert_called()
        self.assertEqual(session.dialog.presentation,'voiceover')
        session.tick_presentation(5)
        self.assertIsNone(session.dialog)

if __name__=='__main__': unittest.main()
