"""ETU comprehension: text evidence -> LessonSpec (closed-set, abstaining).

The reasoning model (DeepSeek, the sole LLM) classifies evidence into a
catalog concept. Visual understanding comes from deterministic CV modules
(mmi/etu/vision/) — NOT from a vision LLM. The CV modules feed structured
data into this classifier.
"""

from mmi.etu.comprehend.classify import Comprehension, comprehend
from mmi.etu.comprehend.evidence import Evidence, gather

__all__ = ["Comprehension", "comprehend", "Evidence", "gather"]
