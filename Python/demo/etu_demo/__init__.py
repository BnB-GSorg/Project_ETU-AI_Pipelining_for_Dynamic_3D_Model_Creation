"""
ETU Demo - AI Pipelining for Dynamic 3D Model Creation

Python demonstration implementation for research and prototyping.
"""

__version__ = "0.1.0"
__author__ = "BnB Organization"

from .pipeline import Pipeline, PipelineConfig, PipelineStage
from .utils import load_input, export_model

__all__ = [
    "Pipeline",
    "PipelineConfig",
    "PipelineStage",
    "load_input",
    "export_model",
    "__version__",
]
