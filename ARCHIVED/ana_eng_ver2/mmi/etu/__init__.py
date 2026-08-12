"""ETU — lift 2D academic explainers into 3D interactive scenes.

comprehend (video -> LessonSpec, future)  ->  author (LessonSpec -> Scene, now)
"""

from mmi.etu.spec import LessonSpec
from mmi.etu.synthesize import synthesize

__all__ = ["LessonSpec", "synthesize"]
