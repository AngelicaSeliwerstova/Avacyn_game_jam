import math
import random
import unittest
from unittest.mock import patch
import glm
from engine.collision.aabb import AABB
from engine.collision.world import CollisionWorld
from engine.collision.world3d import CollisionWorld3D
from engine.scene.box import Box
from engine.scene.object import ObjectState, SceneObject
from game.levels.spiral import SpiralStair
from test_hospital import make_body


class WallSlidingTests(unittest.TestCase):
    def test_diagonal_input_preserves_motion_along_rotated_rail(self):
        for angle in (10,45,80,135,225,315):
            with self.subTest(angle=angle):
                box=Box((0,1,0),(.2,2,16),yaw_degrees=angle)
                world=CollisionWorld((box.footprint,))
                a=math.radians(angle)
                normal=glm.vec3(math.cos(a),0,-math.sin(a))
                tangent=glm.vec3(math.sin(a),0,math.cos(a))
                start=normal*.4-tangent*2
                result=world.move(start,-normal*3+tangent*2.25,.25,.1)
                self.assertAlmostEqual(glm.dot(result-start,tangent),2.25,places=4)
                self.assertAlmostEqual(glm.dot(result,normal),.35,places=4)
                self.assertFalse(world.is_blocked(result,.25-1e-5))

    def test_sliding_does_not_cross_thin_rotated_walls_or_inside_corners(self):
        world=CollisionWorld((Box((0,1,0),(.005,2,20),yaw_degrees=45).footprint,
                              AABB(-6,-6,6,-5.9)),bounds=AABB(-6,-6,6,6))
        position=glm.vec3(-4,0,1)
        rng=random.Random(1981)
        for _ in range(400):
            position=world.move(position,glm.vec3(rng.uniform(-3,3),0,rng.uniform(-3,3)),.25,.1)
            self.assertFalse(world.is_blocked(position,.25-1e-5))

    def test_moving_actor_does_not_rebuild_static_hospital_collision_grid(self):
        fixed=tuple(Box((i*2,1,10),(1,2,1)).collider for i in range(200))
        actor=SceneObject('moving',{'default':ObjectState((Box((1,1,0),(.5,2,.5)),))})
        world=CollisionWorld3D(fixed,objects=(actor,))
        with patch.object(world,'_build_grid',wraps=world._build_grid) as build:
            for i in range(20):
                actor.set_geometry((Box((1+i*.1,1,0),(.5,2,.5)),))
                self.assertFalse(world.is_blocked(glm.vec3(0),.25,1.8))
            self.assertEqual(sum(len(call.args[0])==200 for call in build.call_args_list),1)
        self.assertTrue(world.is_blocked(glm.vec3(2.9,0,0),.25,1.8))

    def test_ascent_and_descent_continue_while_pushing_against_both_rails(self):
        stair=SpiralStair()
        world=CollisionWorld3D(b.collider for b in stair.build())
        for fps in (20,60,120):
            for side,radius in ((-1,1.97),(1,3.8)):
                for descending in (False,True):
                    with self.subTest(fps=fps,side=side,descending=descending):
                        step=28 if descending else 8
                        angle=90-(step+.5)*360/stair.steps
                        point=glm.vec3(stair.point(angle,radius,stair.step_height(step)))
                        point.y=world.support_height(point,.25,point.y+.3)
                        body=make_body(world,tuple(point))
                        previous=math.atan2(point.z-4,point.x+13)
                        progress=0
                        direction=-1 if descending else 1
                        for _ in range(fps*18):
                            theta=math.atan2(body.position.z-4,body.position.x+13)
                            tangent=glm.vec3(math.sin(theta),0,-math.cos(theta))*direction
                            radial=glm.vec3(math.cos(theta),0,math.sin(theta))*side
                            body.update(1/fps,tangent*2.3+radial*.6)
                            theta=math.atan2(body.position.z-4,body.position.x+13)
                            progress+=math.remainder(previous-theta,math.tau)*direction
                            previous=theta
                            self.assertFalse(world.is_blocked(body.position,.25-1e-4,1.8-1e-4))
                            if progress>math.radians(190): break
                        else:
                            self.fail(f'Stuck on rail: {tuple(body.position)}, angular progress={math.degrees(progress)}')
                        if descending: self.assertLess(body.position.y,1.4)
                        else: self.assertGreater(body.position.y,3)


if __name__=='__main__': unittest.main()
