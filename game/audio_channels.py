"""Shared mixer layout keeps ambience, story cues, voices and steps separate."""

MIXER_CHANNELS = 32
STORY_LOOP_CHANNELS = range(4, 7)
ENVIRONMENT_CHANNELS = range(7, 11)
DIALOGUE_CHANNEL = 11
FIRST_FOOTSTEP_CHANNEL = 12
RESERVED_CHANNELS = FIRST_FOOTSTEP_CHANNEL
