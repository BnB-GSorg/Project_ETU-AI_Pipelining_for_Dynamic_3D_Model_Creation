#!/usr/bin/env python3
"""
ETU Demo - Command Line Interface

Usage:
    etu-demo input.png -o output.obj
    etu-demo --help
"""

import argparse
import sys
from pathlib import Path

from . import __version__
from .pipeline import Pipeline, PipelineConfig, PipelineStage


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="etu-demo",
        description="ETU Demo - AI Pipelining for Dynamic 3D Model Creation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    etu-demo input.png -o output.obj
    etu-demo input.png --quality 0.8 --no-gpu
    etu-demo input.png --visualize
        """,
    )

    parser.add_argument("input", nargs="?", type=Path, help="Input file path")
    parser.add_argument(
        "-o", "--output", type=Path, default=None, help="Output file path (default: output.obj)"
    )
    parser.add_argument(
        "--quality",
        type=float,
        default=1.0,
        help="Quality level 0.0-1.0 (default: 1.0)",
    )
    parser.add_argument(
        "--no-gpu",
        action="store_true",
        help="Disable GPU acceleration",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Show visualization of the result",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return parser


def progress_callback(stage: PipelineStage, progress: float, message: str) -> None:
    """Print progress updates."""
    stage_names = {
        PipelineStage.INPUT: "Input",
        PipelineStage.PREPROCESS: "Preprocess",
        PipelineStage.INFERENCE: "Inference",
        PipelineStage.POSTPROCESS: "PostProcess",
        PipelineStage.RENDERING: "Rendering",
        PipelineStage.OUTPUT: "Output",
    }
    name = stage_names.get(stage, "Unknown")
    print(f"\r[{name}] {int(progress * 100):3d}% - {message}", end="", flush=True)


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Print banner
    print(f"ETU Demo v{__version__}")
    print("=" * 40)

    # Check input
    if args.input is None:
        print("\nNo input file specified. Running in demo mode...\n")
        run_demo(args)
        return 0

    if not args.input.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        return 1

    # Configure pipeline
    config = PipelineConfig(
        use_gpu=not args.no_gpu,
        quality=args.quality,
    )

    print(f"\nConfiguration:")
    print(f"  GPU: {'Enabled' if config.use_gpu else 'Disabled'}")
    print(f"  Quality: {config.quality}")
    print(f"  Input: {args.input}")
    print()

    # Create and run pipeline
    pipeline = Pipeline(config)
    if args.verbose:
        pipeline.set_progress_callback(progress_callback)

    try:
        model = pipeline.process(args.input)
        print()  # New line after progress
    except Exception as e:
        print(f"\nError during processing: {e}", file=sys.stderr)
        return 1

    # Export result
    output_path = args.output or Path("output.obj")
    try:
        from .utils import export_model

        export_model(model, output_path)
        print(f"\nOutput saved to: {output_path}")
    except Exception as e:
        print(f"\nError saving output: {e}", file=sys.stderr)
        return 1

    # Visualize if requested
    if args.visualize:
        try:
            visualize_model(model)
        except ImportError:
            print("Visualization requires: pip install etu-demo[viz]", file=sys.stderr)

    print("\nDone!")
    return 0


def run_demo(args: argparse.Namespace) -> None:
    """Run in demo mode without input file."""
    import numpy as np

    config = PipelineConfig(
        use_gpu=not args.no_gpu,
        quality=args.quality,
    )

    print("Creating demo pipeline...")
    pipeline = Pipeline(config)
    pipeline.set_progress_callback(progress_callback)

    # Create dummy input
    print("\nProcessing dummy input...")
    dummy_input = np.random.rand(256, 256, 3).astype(np.float32)
    model = pipeline.process_array(dummy_input)

    print(f"\n\nGenerated model:")
    print(f"  Vertices: {len(model.vertices)}")
    print(f"  Faces: {len(model.faces)}")

    if args.visualize:
        try:
            visualize_model(model)
        except ImportError:
            print("\nVisualization requires: pip install etu-demo[viz]")


def visualize_model(model) -> None:
    """Visualize the generated model."""
    try:
        import trimesh

        mesh = trimesh.Trimesh(vertices=model.vertices, faces=model.faces)
        mesh.show()
    except ImportError:
        print("Install trimesh for visualization: pip install trimesh pyglet")


if __name__ == "__main__":
    sys.exit(main())
