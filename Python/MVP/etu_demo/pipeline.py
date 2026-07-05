"""
ETU Demo - Pipeline Module

Core AI pipeline for dynamic 3D model creation.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Callable, Optional, Union

import numpy as np


class PipelineStage(Enum):
    """Pipeline processing stages."""

    INPUT = auto()
    PREPROCESS = auto()
    INFERENCE = auto()
    POSTPROCESS = auto()
    RENDERING = auto()
    OUTPUT = auto()


@dataclass
class PipelineConfig:
    """Configuration for the AI pipeline."""

    use_gpu: bool = True
    batch_size: int = 1
    max_vertices: int = 1_000_000
    max_triangles: int = 500_000
    quality: float = 1.0  # 0.0 - 1.0
    enable_caching: bool = True
    cache_directory: Optional[Path] = None


@dataclass
class Model:
    """Generated 3D model."""

    vertices: np.ndarray  # (N, 3) float32
    faces: np.ndarray  # (M, 3) int32
    normals: Optional[np.ndarray] = None  # (N, 3) float32
    colors: Optional[np.ndarray] = None  # (N, 4) float32 RGBA
    uvs: Optional[np.ndarray] = None  # (N, 2) float32
    name: str = "generated_model"

    @property
    def num_vertices(self) -> int:
        """Number of vertices."""
        return len(self.vertices)

    @property
    def num_faces(self) -> int:
        """Number of faces (triangles)."""
        return len(self.faces)

    def compute_normals(self) -> None:
        """Compute vertex normals from faces."""
        # Simple per-face normal calculation
        v0 = self.vertices[self.faces[:, 0]]
        v1 = self.vertices[self.faces[:, 1]]
        v2 = self.vertices[self.faces[:, 2]]

        face_normals = np.cross(v1 - v0, v2 - v0)
        norms = np.linalg.norm(face_normals, axis=1, keepdims=True)
        face_normals = face_normals / (norms + 1e-8)

        # Average to vertices
        vertex_normals = np.zeros_like(self.vertices)
        for i, face in enumerate(self.faces):
            for vi in face:
                vertex_normals[vi] += face_normals[i]

        norms = np.linalg.norm(vertex_normals, axis=1, keepdims=True)
        self.normals = vertex_normals / (norms + 1e-8)


# Type alias for progress callback
ProgressCallback = Callable[[PipelineStage, float, str], None]


class Pipeline:
    """
    AI Pipeline for dynamic 3D model creation.

    This pipeline processes input data through multiple stages:
    1. Input loading and validation
    2. Preprocessing and feature extraction
    3. AI model inference
    4. Post-processing and mesh generation
    5. Rendering preparation
    6. Final output
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        """Initialize pipeline with configuration."""
        self.config = config or PipelineConfig()
        self._progress_callback: Optional[ProgressCallback] = None
        self._is_processing = False
        self._cancel_requested = False

        # Initialize GPU if available
        self._device = self._init_device()

    def _init_device(self) -> str:
        """Initialize compute device."""
        if not self.config.use_gpu:
            return "cpu"

        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
            elif torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass

        return "cpu"

    def set_progress_callback(self, callback: ProgressCallback) -> None:
        """Set callback for progress updates."""
        self._progress_callback = callback

    def _report_progress(self, stage: PipelineStage, progress: float, message: str) -> None:
        """Report progress to callback."""
        if self._progress_callback:
            self._progress_callback(stage, progress, message)

    def process(self, input_path: Union[str, Path]) -> Model:
        """
        Process input file and generate 3D model.

        Args:
            input_path: Path to input file (image, point cloud, etc.)

        Returns:
            Generated 3D model

        Raises:
            FileNotFoundError: If input file doesn't exist
            ValueError: If input format is unsupported
            RuntimeError: If processing fails
        """
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Load input
        self._report_progress(PipelineStage.INPUT, 0.0, "Loading input...")
        from .utils import load_input

        input_data = load_input(input_path)
        self._report_progress(PipelineStage.INPUT, 1.0, "Input loaded")

        return self.process_array(input_data)

    def process_array(self, input_data: np.ndarray) -> Model:
        """
        Process numpy array input and generate 3D model.

        Args:
            input_data: Input data as numpy array

        Returns:
            Generated 3D model
        """
        if self._is_processing:
            raise RuntimeError("Pipeline is already processing")

        self._is_processing = True
        self._cancel_requested = False

        try:
            return self._execute_pipeline(input_data)
        finally:
            self._is_processing = False

    def _execute_pipeline(self, input_data: np.ndarray) -> Model:
        """Execute the full pipeline."""
        # Stage 2: Preprocess
        self._report_progress(PipelineStage.PREPROCESS, 0.0, "Preprocessing...")
        processed = self._preprocess(input_data)
        self._report_progress(PipelineStage.PREPROCESS, 1.0, "Preprocessing complete")

        if self._cancel_requested:
            raise RuntimeError("Pipeline cancelled")

        # Stage 3: Inference
        self._report_progress(PipelineStage.INFERENCE, 0.0, "Running inference...")
        features = self._inference(processed)
        self._report_progress(PipelineStage.INFERENCE, 1.0, "Inference complete")

        if self._cancel_requested:
            raise RuntimeError("Pipeline cancelled")

        # Stage 4: Post-process (mesh generation)
        self._report_progress(PipelineStage.POSTPROCESS, 0.0, "Generating mesh...")
        model = self._postprocess(features)
        self._report_progress(PipelineStage.POSTPROCESS, 1.0, "Mesh generated")

        if self._cancel_requested:
            raise RuntimeError("Pipeline cancelled")

        # Stage 5: Prepare for rendering
        self._report_progress(PipelineStage.RENDERING, 0.0, "Preparing render data...")
        model.compute_normals()
        self._report_progress(PipelineStage.RENDERING, 1.0, "Render data ready")

        # Stage 6: Output
        self._report_progress(PipelineStage.OUTPUT, 1.0, "Complete!")

        return model

    def _preprocess(self, input_data: np.ndarray) -> np.ndarray:
        """Preprocess input data."""
        # Normalize to [0, 1]
        data = input_data.astype(np.float32)
        data = (data - data.min()) / (data.max() - data.min() + 1e-8)
        return data

    def _inference(self, data: np.ndarray) -> np.ndarray:
        """Run AI model inference."""
        # TODO: Replace with actual AI model
        # For demo, generate random features
        np.random.seed(42)  # For reproducibility
        features = np.random.rand(64, 64, 64).astype(np.float32)

        # Apply quality scaling
        if self.config.quality < 1.0:
            scale = int(64 * self.config.quality)
            scale = max(16, scale)  # Minimum 16^3
            features = features[:scale, :scale, :scale]

        return features

    def _postprocess(self, features: np.ndarray) -> Model:
        """Generate mesh from features using marching cubes."""
        try:
            # Try to use scikit-image marching cubes
            from skimage import measure

            threshold = 0.5
            verts, faces, normals, _ = measure.marching_cubes(
                features, level=threshold, allow_degenerate=False
            )

            # Center and normalize
            verts = verts - verts.mean(axis=0)
            scale = np.abs(verts).max()
            if scale > 0:
                verts = verts / scale

            return Model(
                vertices=verts.astype(np.float32),
                faces=faces.astype(np.int32),
                normals=normals.astype(np.float32),
                name="generated_model",
            )

        except ImportError:
            # Fallback: generate simple cube
            return self._generate_cube()

    def _generate_cube(self) -> Model:
        """Generate a simple cube mesh (fallback)."""
        vertices = np.array(
            [
                [-1, -1, -1],
                [1, -1, -1],
                [1, 1, -1],
                [-1, 1, -1],
                [-1, -1, 1],
                [1, -1, 1],
                [1, 1, 1],
                [-1, 1, 1],
            ],
            dtype=np.float32,
        )

        faces = np.array(
            [
                [0, 1, 2],
                [0, 2, 3],  # front
                [4, 6, 5],
                [4, 7, 6],  # back
                [0, 4, 5],
                [0, 5, 1],  # bottom
                [2, 6, 7],
                [2, 7, 3],  # top
                [0, 3, 7],
                [0, 7, 4],  # left
                [1, 5, 6],
                [1, 6, 2],  # right
            ],
            dtype=np.int32,
        )

        return Model(vertices=vertices, faces=faces, name="cube")

    def cancel(self) -> None:
        """Request cancellation of ongoing processing."""
        self._cancel_requested = True

    @property
    def is_processing(self) -> bool:
        """Check if pipeline is currently processing."""
        return self._is_processing

    @property
    def device(self) -> str:
        """Get the compute device being used."""
        return self._device
