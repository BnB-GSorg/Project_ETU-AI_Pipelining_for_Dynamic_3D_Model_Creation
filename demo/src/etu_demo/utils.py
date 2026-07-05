"""
ETU Demo - Utility Functions

Helper functions for input/output and common operations.
"""

from pathlib import Path
from typing import Union

import numpy as np


def load_input(path: Union[str, Path]) -> np.ndarray:
    """
    Load input file and return as numpy array.

    Supports:
    - Images: .png, .jpg, .jpeg, .bmp, .tiff
    - Point clouds: .ply, .pcd, .xyz
    - NumPy arrays: .npy, .npz

    Args:
        path: Path to input file

    Returns:
        Input data as numpy array

    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If format is unsupported
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    suffix = path.suffix.lower()

    # Image formats
    if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}:
        return _load_image(path)

    # NumPy formats
    if suffix == ".npy":
        return np.load(path)
    if suffix == ".npz":
        data = np.load(path)
        # Return first array in the archive
        return data[list(data.keys())[0]]

    # Point cloud formats
    if suffix in {".ply", ".pcd", ".xyz"}:
        return _load_point_cloud(path)

    raise ValueError(f"Unsupported input format: {suffix}")


def _load_image(path: Path) -> np.ndarray:
    """Load image file."""
    try:
        from PIL import Image

        img = Image.open(path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        return np.array(img, dtype=np.float32) / 255.0
    except ImportError:
        raise ImportError("Pillow is required for image loading: pip install pillow")


def _load_point_cloud(path: Path) -> np.ndarray:
    """Load point cloud file."""
    suffix = path.suffix.lower()

    if suffix == ".xyz":
        # Simple XYZ format: one point per line, space-separated
        return np.loadtxt(path, dtype=np.float32)

    if suffix == ".ply":
        try:
            import trimesh

            mesh = trimesh.load(path)
            if hasattr(mesh, "vertices"):
                return np.array(mesh.vertices, dtype=np.float32)
            return np.array(mesh, dtype=np.float32)
        except ImportError:
            raise ImportError("trimesh is required for PLY loading: pip install trimesh")

    if suffix == ".pcd":
        try:
            import open3d as o3d

            pcd = o3d.io.read_point_cloud(str(path))
            return np.asarray(pcd.points, dtype=np.float32)
        except ImportError:
            raise ImportError("open3d is required for PCD loading: pip install open3d")

    raise ValueError(f"Unsupported point cloud format: {suffix}")


def export_model(model, path: Union[str, Path], format: str = None) -> None:
    """
    Export 3D model to file.

    Supports:
    - Wavefront OBJ: .obj
    - Stanford PLY: .ply
    - STL: .stl
    - GLTF: .gltf, .glb

    Args:
        model: Model object with vertices and faces
        path: Output file path
        format: Override output format (auto-detected from extension if None)

    Raises:
        ValueError: If format is unsupported
    """
    path = Path(path)
    suffix = format or path.suffix.lower()

    if suffix == ".obj":
        _export_obj(model, path)
    elif suffix == ".ply":
        _export_ply(model, path)
    elif suffix == ".stl":
        _export_stl(model, path)
    elif suffix in {".gltf", ".glb"}:
        _export_gltf(model, path)
    else:
        # Try trimesh for other formats
        _export_trimesh(model, path)


def _export_obj(model, path: Path) -> None:
    """Export to Wavefront OBJ format."""
    with open(path, "w") as f:
        f.write(f"# ETU Demo - Generated Model\n")
        f.write(f"# Vertices: {len(model.vertices)}\n")
        f.write(f"# Faces: {len(model.faces)}\n\n")

        # Write vertices
        for v in model.vertices:
            f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")

        # Write normals if available
        if model.normals is not None:
            f.write("\n")
            for n in model.normals:
                f.write(f"vn {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}\n")

        # Write texture coordinates if available
        if model.uvs is not None:
            f.write("\n")
            for uv in model.uvs:
                f.write(f"vt {uv[0]:.6f} {uv[1]:.6f}\n")

        # Write faces (OBJ uses 1-based indexing)
        f.write("\n")
        for face in model.faces:
            if model.normals is not None:
                f.write(
                    f"f {face[0] + 1}//{face[0] + 1} {face[1] + 1}//{face[1] + 1} {face[2] + 1}//{face[2] + 1}\n"
                )
            else:
                f.write(f"f {face[0] + 1} {face[1] + 1} {face[2] + 1}\n")


def _export_ply(model, path: Path) -> None:
    """Export to Stanford PLY format."""
    try:
        import trimesh

        mesh = trimesh.Trimesh(
            vertices=model.vertices,
            faces=model.faces,
            vertex_normals=model.normals,
        )
        mesh.export(path)
    except ImportError:
        # Fallback: write ASCII PLY manually
        with open(path, "w") as f:
            f.write("ply\n")
            f.write("format ascii 1.0\n")
            f.write(f"element vertex {len(model.vertices)}\n")
            f.write("property float x\n")
            f.write("property float y\n")
            f.write("property float z\n")
            f.write(f"element face {len(model.faces)}\n")
            f.write("property list uchar int vertex_indices\n")
            f.write("end_header\n")

            for v in model.vertices:
                f.write(f"{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")

            for face in model.faces:
                f.write(f"3 {face[0]} {face[1]} {face[2]}\n")


def _export_stl(model, path: Path) -> None:
    """Export to STL format."""
    try:
        import trimesh

        mesh = trimesh.Trimesh(vertices=model.vertices, faces=model.faces)
        mesh.export(path)
    except ImportError:
        raise ImportError("trimesh is required for STL export: pip install trimesh")


def _export_gltf(model, path: Path) -> None:
    """Export to GLTF/GLB format."""
    try:
        import trimesh

        mesh = trimesh.Trimesh(
            vertices=model.vertices,
            faces=model.faces,
            vertex_normals=model.normals,
        )
        mesh.export(path)
    except ImportError:
        raise ImportError("trimesh is required for GLTF export: pip install trimesh")


def _export_trimesh(model, path: Path) -> None:
    """Export using trimesh for various formats."""
    try:
        import trimesh

        mesh = trimesh.Trimesh(
            vertices=model.vertices,
            faces=model.faces,
            vertex_normals=model.normals,
        )
        mesh.export(path)
    except ImportError:
        raise ImportError(f"trimesh is required for {path.suffix} export: pip install trimesh")


def create_grid(size: int = 64, spacing: float = 1.0) -> np.ndarray:
    """
    Create a 3D grid of points.

    Args:
        size: Number of points per dimension
        spacing: Distance between points

    Returns:
        (size^3, 3) array of grid points
    """
    x = np.linspace(0, (size - 1) * spacing, size)
    y = np.linspace(0, (size - 1) * spacing, size)
    z = np.linspace(0, (size - 1) * spacing, size)

    xx, yy, zz = np.meshgrid(x, y, z, indexing="ij")
    return np.stack([xx.ravel(), yy.ravel(), zz.ravel()], axis=1).astype(np.float32)


def normalize_vertices(vertices: np.ndarray, center: bool = True, scale: bool = True) -> np.ndarray:
    """
    Normalize vertices to fit in unit cube.

    Args:
        vertices: (N, 3) vertex positions
        center: Center vertices at origin
        scale: Scale to fit in [-1, 1]^3

    Returns:
        Normalized vertices
    """
    vertices = vertices.copy()

    if center:
        vertices -= vertices.mean(axis=0)

    if scale:
        max_extent = np.abs(vertices).max()
        if max_extent > 0:
            vertices /= max_extent

    return vertices
