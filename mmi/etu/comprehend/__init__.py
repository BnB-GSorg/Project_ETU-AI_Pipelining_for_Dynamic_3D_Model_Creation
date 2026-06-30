"""ETU comprehension: 2D video evidence -> LessonSpec (closed-set, abstaining).

Hybrid path: a vision "eye" (describe_frames) turns frames into a description,
which joins transcript/OCR as text evidence for the DeepSeek "brain" (comprehend).
"""

from mmi.etu.comprehend.classify import Comprehension, comprehend
from mmi.etu.comprehend.evidence import Evidence, gather
from mmi.etu.comprehend.vision import describe_frames

__all__ = ["Comprehension", "comprehend", "Evidence", "gather", "describe_frames"]
