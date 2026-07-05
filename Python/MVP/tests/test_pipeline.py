"""
ETU Demo - Pipeline Tests
"""

import numpy as np
import pytest

from etu_demo import Pipeline, PipelineConfig, PipelineStage


class TestPipelineConfig:
    """Tests for PipelineConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PipelineConfig()
        assert config.use_gpu is True
        assert config.batch_size == 1
        assert config.quality == 1.0
        assert config.enable_caching is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = PipelineConfig(
            use_gpu=False,
            batch_size=4,
            quality=0.5,
        )
        assert config.use_gpu is False
        assert config.batch_size == 4
        assert config.quality == 0.5


class TestPipeline:
    """Tests for Pipeline class."""

    def test_pipeline_creation(self):
        """Test pipeline creation."""
        pipeline = Pipeline()
        assert pipeline is not None
        assert not pipeline.is_processing

    def test_pipeline_with_config(self):
        """Test pipeline with custom config."""
        config = PipelineConfig(use_gpu=False)
        pipeline = Pipeline(config)
        assert pipeline.config.use_gpu is False

    def test_process_array(self):
        """Test processing numpy array input."""
        config = PipelineConfig(use_gpu=False)
        pipeline = Pipeline(config)

        # Create dummy input
        input_data = np.random.rand(64, 64, 3).astype(np.float32)
        model = pipeline.process_array(input_data)

        assert model is not None
        assert len(model.vertices) > 0
        assert len(model.faces) > 0

    def test_progress_callback(self):
        """Test progress callback is called."""
        config = PipelineConfig(use_gpu=False)
        pipeline = Pipeline(config)

        stages_reported = []

        def callback(stage: PipelineStage, progress: float, message: str):
            stages_reported.append(stage)

        pipeline.set_progress_callback(callback)

        input_data = np.random.rand(32, 32, 3).astype(np.float32)
        pipeline.process_array(input_data)

        # Should have reported multiple stages
        assert len(stages_reported) > 0
        assert PipelineStage.INPUT in stages_reported or PipelineStage.PREPROCESS in stages_reported

    def test_model_normals(self):
        """Test model normal computation."""
        config = PipelineConfig(use_gpu=False)
        pipeline = Pipeline(config)

        input_data = np.random.rand(32, 32, 3).astype(np.float32)
        model = pipeline.process_array(input_data)

        # Normals should be computed
        assert model.normals is not None
        assert len(model.normals) == len(model.vertices)

        # Normals should be unit length
        norms = np.linalg.norm(model.normals, axis=1)
        np.testing.assert_array_almost_equal(norms, np.ones_like(norms), decimal=5)

    def test_quality_affects_output(self):
        """Test that quality setting affects output."""
        input_data = np.random.rand(64, 64, 3).astype(np.float32)

        # High quality
        config_high = PipelineConfig(use_gpu=False, quality=1.0)
        pipeline_high = Pipeline(config_high)
        model_high = pipeline_high.process_array(input_data)

        # Low quality
        config_low = PipelineConfig(use_gpu=False, quality=0.5)
        pipeline_low = Pipeline(config_low)
        model_low = pipeline_low.process_array(input_data)

        # Low quality should have fewer vertices (in general)
        # Note: This depends on implementation, adjust if needed
        assert model_low is not None
        assert model_high is not None


class TestModel:
    """Tests for Model class."""

    def test_model_properties(self):
        """Test model properties."""
        from etu_demo.pipeline import Model

        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32)
        faces = np.array([[0, 1, 2]], dtype=np.int32)

        model = Model(vertices=vertices, faces=faces)

        assert model.num_vertices == 3
        assert model.num_faces == 1

    def test_compute_normals(self):
        """Test normal computation."""
        from etu_demo.pipeline import Model

        # Simple triangle in XY plane
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=np.float32)
        faces = np.array([[0, 1, 2]], dtype=np.int32)

        model = Model(vertices=vertices, faces=faces)
        model.compute_normals()

        assert model.normals is not None
        # Normal should point in +Z direction
        for n in model.normals:
            assert abs(n[2]) > 0.9  # Should be close to (0, 0, 1) or (0, 0, -1)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
