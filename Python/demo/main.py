# Demo, by MCHIGM
# Works by generating multiple 3D models and making it to a step-motion video
# Using a multi-engine architecture: VTK, Open CASCADE, ABAQUS, AutoCAD
#
# Install notes (Python 3.14, conda env at ../Project-ETU):
#   VTK         : pre-installed (vtk 9.6.1)
#   Open CASCADE: pythonocc-core — installed ✓ (STEP/IGES/BREP/STL/OBJ)
#   ABAQUS      : requires Abaqus CAE + Python API on system PATH
#   AutoCAD     : ezdxf installed ✓ (DXF); COM mode needs AutoCAD + pywin32
#
# Usage:
#   .\Python\Project-ETU\python.exe Python/demo/main.py --list-engines
#   .\Python\Project-ETU\python.exe Python/demo/main.py --engine vtk
#   .\Python\Project-ETU\python.exe Python/demo/main.py --engine opencascade --format step
#   .\Python\Project-ETU\python.exe Python/demo/main.py --engine ezdxf --format dxf


import sys
import os
import abc
import argparse
from dataclasses import dataclass, field
from typing import Optional, Callable

# ── ensure we're running inside the Project-ETU conda environment ─────
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONDA_PYTHON = os.path.join(_PROJECT_ROOT, "Project-ETU", "python.exe")
_CONDA_LIB = os.path.join(_PROJECT_ROOT, "Project-ETU", "Lib", "site-packages")

if os.path.normcase(sys.executable) != os.path.normcase(_CONDA_PYTHON):
    sys.exit(
        f"\n⚠  Wrong Python interpreter detected!\n"
        f"   Current : {sys.executable} ({sys.version_info.major}.{sys.version_info.minor})\n"
        f"   Required: {_CONDA_PYTHON} (3.14)\n\n"
        f"   Please run with:\n"
        f"     .\\Python\\Project-ETU\\python.exe .\\Python\\demo\\main.py --list-engines\n"
    )

# DLL search paths — VTK and other native libs live in Library/bin
_DLL_DIR = os.path.join(_PROJECT_ROOT, "Project-ETU", "DLLs")
_LIB_BIN_DIR = os.path.join(_PROJECT_ROOT, "Project-ETU", "Library", "bin")
for _dll in (_DLL_DIR, _LIB_BIN_DIR):
    if os.path.isdir(_dll) and hasattr(os, "add_dll_directory"):
        os.add_dll_directory(_dll)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Common data model
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class MeshData:
    """Portable mesh container shared by all engine adapters."""
    vertices: list   # [(x,y,z), ...]
    faces: list      # [(i,j,k), ...]  triangle indices
    normals: Optional[list] = None
    name: str = "model"


@dataclass
class EngineInfo:
    """Metadata about an available engine."""
    key: str
    name: str
    available: bool
    notes: str = ""


# ═══════════════════════════════════════════════════════════════════════════
# 2. Abstract engine interface
# ═══════════════════════════════════════════════════════════════════════════

class EngineInterface(abc.ABC):
    """All 3D engines must implement this protocol."""

    @abc.abstractmethod
    def create_model(self, config: dict) -> MeshData:
        """Generate a single 3D model from a configuration dict."""
        ...

    @abc.abstractmethod
    def export_model(self, mesh: MeshData, filepath: str, fmt: str = "obj") -> str:
        """Export mesh to file; returns the filepath written."""
        ...

    def supports_format(self, fmt: str) -> bool:
        return fmt.lower() in ("obj", "stl")


# ═══════════════════════════════════════════════════════════════════════════
# 3. VTK Engine (primary — already installed)
# ═══════════════════════════════════════════════════════════════════════════

class VTKEngine(EngineInterface):
    """3D model creation using VTK (Visualization Toolkit)."""

    def __init__(self):
        import vtk
        self.vtk = vtk

    def create_model(self, config: dict) -> MeshData:
        import vtk
        import numpy as np

        shape = config.get("shape", "sphere")
        resolution = config.get("resolution", 32)
        size = config.get("size", 1.0)

        source = self._make_source(shape, resolution, size)
        source.Update()

        polydata = source.GetOutput()
        points = polydata.GetPoints()
        polys = polydata.GetPolys()

        vertices = [(points.GetPoint(i)[0], points.GetPoint(i)[1], points.GetPoint(i)[2])
                    for i in range(points.GetNumberOfPoints())]
        faces = []
        polys.InitTraversal()
        id_list = vtk.vtkIdList()
        while polys.GetNextCell(id_list):
            if id_list.GetNumberOfIds() == 3:
                faces.append((id_list.GetId(0), id_list.GetId(1), id_list.GetId(2)))

        return MeshData(vertices=vertices, faces=faces, name=f"{shape}_{resolution}")

    def _make_source(self, shape: str, resolution: int, size: float):
        import vtk
        shape = shape.lower()
        if shape == "sphere":
            src = vtk.vtkSphereSource()
            src.SetThetaResolution(resolution)
            src.SetPhiResolution(resolution)
            src.SetRadius(size)
        elif shape == "cube":
            src = vtk.vtkCubeSource()
            src.SetXLength(size)
            src.SetYLength(size)
            src.SetZLength(size)
        elif shape == "cylinder":
            src = vtk.vtkCylinderSource()
            src.SetResolution(resolution)
            src.SetRadius(size * 0.5)
            src.SetHeight(size)
        elif shape == "cone":
            src = vtk.vtkConeSource()
            src.SetResolution(resolution)
            src.SetRadius(size * 0.5)
            src.SetHeight(size)
        elif shape == "torus":
            torus = vtk.vtkParametricTorus()
            torus.SetRingRadius(size * 0.6)
            torus.SetCrossSectionRadius(size * 0.2)
            src = vtk.vtkParametricFunctionSource()
            src.SetParametricFunction(torus)
            src.SetScalarModeToZ()
        else:
            src = vtk.vtkSphereSource()
            src.SetThetaResolution(resolution)
            src.SetPhiResolution(resolution)
            src.SetRadius(size)
        return src

    def export_model(self, mesh: MeshData, filepath: str, fmt: str = "obj") -> str:
        import vtk
        polydata = self._mesh_to_polydata(mesh)

        filepath = filepath if filepath.endswith(f".{fmt}") else f"{filepath}.{fmt}"
        if fmt == "obj":
            writer = vtk.vtkOBJWriter()
        elif fmt == "stl":
            writer = vtk.vtkSTLWriter()
        else:
            writer = vtk.vtkOBJWriter()

        writer.SetFileName(filepath)
        writer.SetInputData(polydata)
        writer.Write()
        return filepath

    def _mesh_to_polydata(self, mesh: MeshData):
        import vtk
        points = vtk.vtkPoints()
        for v in mesh.vertices:
            points.InsertNextPoint(v[0], v[1], v[2])

        triangles = vtk.vtkCellArray()
        for f in mesh.faces:
            tri = vtk.vtkTriangle()
            tri.GetPointIds().SetId(0, f[0])
            tri.GetPointIds().SetId(1, f[1])
            tri.GetPointIds().SetId(2, f[2])
            triangles.InsertNextCell(tri)

        polydata = vtk.vtkPolyData()
        polydata.SetPoints(points)
        polydata.SetPolys(triangles)
        return polydata

    def supports_format(self, fmt: str) -> bool:
        return fmt.lower() in ("obj", "stl", "vtp", "ply")


# ═══════════════════════════════════════════════════════════════════════════
# 4. Open CASCADE Engine (pythonocc-core — installed ✓)
# ═══════════════════════════════════════════════════════════════════════════

class OpenCASCADEEngine(EngineInterface):
    """Open CASCADE Technology via pythonocc-core.

    Provides precise CAD geometry (BREP solids) and exports to STEP, IGES,
    BREP, STL, and OBJ.  Uses OCC's tessellator for mesh extraction.
    """

    def __init__(self):
        from OCC.Core.BRepPrimAPI import (
            BRepPrimAPI_MakeSphere,
            BRepPrimAPI_MakeBox,
            BRepPrimAPI_MakeCylinder,
            BRepPrimAPI_MakeCone,
            BRepPrimAPI_MakeTorus,
        )
        from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
        from OCC.Core.TopExp import TopExp_Explorer
        from OCC.Core.TopAbs import TopAbs_FACE
        from OCC.Core.BRep import BRep_Tool
        from OCC.Core.TopLoc import TopLoc_Location
        from OCC.Core.gp import gp_Ax2, gp_Dir, gp_Pnt
        self._brep = True
        # store refs so GC doesn't eat them
        self._BRepPrimAPI_MakeSphere = BRepPrimAPI_MakeSphere
        self._BRepPrimAPI_MakeBox = BRepPrimAPI_MakeBox
        self._BRepPrimAPI_MakeCylinder = BRepPrimAPI_MakeCylinder
        self._BRepPrimAPI_MakeCone = BRepPrimAPI_MakeCone
        self._BRepPrimAPI_MakeTorus = BRepPrimAPI_MakeTorus
        self._BRepMesh_IncrementalMesh = BRepMesh_IncrementalMesh
        self._TopExp_Explorer = TopExp_Explorer
        self._TopAbs_FACE = TopAbs_FACE
        self._BRep_Tool = BRep_Tool
        self._TopLoc_Location = TopLoc_Location
        self._gp = type("gp", (), {"Ax2": gp_Ax2, "Dir": gp_Dir, "Pnt": gp_Pnt})()

    def create_model(self, config: dict) -> MeshData:
        shape_type = config.get("shape", "sphere")
        size = config.get("size", 1.0)

        bld = self._build_brep(shape_type, size)
        shape = bld.Shape()

        # tessellate
        from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
        BRepMesh_IncrementalMesh(shape, 0.1).Perform()

        # extract mesh
        verts, faces_list = self._extract_mesh(shape)
        return MeshData(vertices=verts, faces=faces_list, name=f"{shape_type}_occ")

    def _build_brep(self, shape_type: str, size: float):
        """Build a BREP solid for the requested shape."""
        s = shape_type.lower()
        if s == "sphere":
            return self._BRepPrimAPI_MakeSphere(size)
        elif s in ("cube", "box"):
            return self._BRepPrimAPI_MakeBox(size, size, size)
        elif s == "cylinder":
            return self._BRepPrimAPI_MakeCylinder(size * 0.5, size)
        elif s == "cone":
            return self._BRepPrimAPI_MakeCone(size * 0.5, size * 0.1, size)
        elif s == "torus":
            return self._BRepPrimAPI_MakeTorus(size * 0.6, size * 0.2)
        else:
            return self._BRepPrimAPI_MakeSphere(size)

    def _extract_mesh(self, shape):
        """Extract triangle mesh from a tessellated TopoDS_Shape."""
        bt = self._BRep_Tool()
        exp = self._TopExp_Explorer(shape, self._TopAbs_FACE)
        verts: list = []
        faces_list: list = []
        while exp.More():
            face = exp.Current()
            loc = self._TopLoc_Location()
            tri = bt.Triangulation(face, loc)
            if tri is not None:
                n_verts = tri.NbNodes()
                n_tris = tri.NbTriangles()
                base = len(verts)
                for i in range(1, n_verts + 1):
                    v = tri.Node(i)
                    verts.append((v.X(), v.Y(), v.Z()))
                for i in range(1, n_tris + 1):
                    t = tri.Triangle(i)
                    faces_list.append((
                        base + t.Value(1) - 1,
                        base + t.Value(2) - 1,
                        base + t.Value(3) - 1,
                    ))
            exp.Next()
        return verts, faces_list

    def export_model(self, mesh: MeshData, filepath: str, fmt: str = "step") -> str:
        fmt = fmt.lower()
        filepath = filepath if filepath.endswith(f".{fmt}") else f"{filepath}.{fmt}"

        if fmt in ("step", "stp"):
            return self._export_step(mesh, filepath)
        elif fmt in ("iges", "igs"):
            return self._export_iges(mesh, filepath)
        elif fmt == "brep":
            return self._export_brep(mesh, filepath)
        elif fmt == "stl":
            return self._export_stl(mesh, filepath)
        elif fmt == "obj":
            return self._export_obj(mesh, filepath)
        else:
            raise ValueError(f"Unsupported format: {fmt}")

    def _mesh_to_brep_shape(self, mesh: MeshData):
        """Reconstruct a basic BREP solid from a Poly_Triangulation.

        This rebuilds a sphere/cube/cylinder approximation for export
        because proper BREP export needs the original topology.
        For demo purposes we rebuild the shape from config-like dimensions.
        """
        # fall back to building fresh — the MeshData carries a name hint
        shape_type = mesh.name.split("_")[0] if "_" in mesh.name else "sphere"
        size = 1.0
        # estimate size from vertex spread
        if mesh.vertices:
            xs = [v[0] for v in mesh.vertices]
            ys = [v[1] for v in mesh.vertices]
            zs = [v[2] for v in mesh.vertices]
            size = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)) / 2.0
            size = max(size, 0.1)
        bld = self._build_brep(shape_type, size)
        return bld.Shape()

    def _export_step(self, mesh: MeshData, filepath: str) -> str:
        from OCC.Core.STEPControl import STEPControl_Writer, STEPControl_AsIs
        from OCC.Core.Interface import Interface_Static
        shape = self._mesh_to_brep_shape(mesh)
        Interface_Static.SetCVal("write.step.schema", "AP203")
        writer = STEPControl_Writer()
        writer.Transfer(shape, STEPControl_AsIs)
        writer.Write(filepath)
        return filepath

    def _export_iges(self, mesh: MeshData, filepath: str) -> str:
        from OCC.Core.IGESControl import IGESControl_Writer
        shape = self._mesh_to_brep_shape(mesh)
        writer = IGESControl_Writer()
        writer.AddShape(shape)
        writer.Write(filepath)
        return filepath

    def _export_brep(self, mesh: MeshData, filepath: str) -> str:
        from OCC.Core.BRepTools import breptools
        shape = self._mesh_to_brep_shape(mesh)
        breptools.Write(shape, filepath)
        return filepath

    def _export_stl(self, mesh: MeshData, filepath: str) -> str:
        from OCC.Core.StlAPI import StlAPI_Writer
        shape = self._mesh_to_brep_shape(mesh)
        writer = StlAPI_Writer()
        writer.Write(shape, filepath)
        return filepath

    def _export_obj(self, mesh: MeshData, filepath: str) -> str:
        # simple OBJ writer — no external deps needed
        with open(filepath, "w") as f:
            f.write(f"# ETU OpenCASCADE OBJ  —  {mesh.name}\n")
            for v in mesh.vertices:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            for face in mesh.faces:
                f.write(f"f {face[0] + 1} {face[1] + 1} {face[2] + 1}\n")
        return filepath

    def supports_format(self, fmt: str) -> bool:
        return fmt.lower() in ("step", "stp", "iges", "igs", "brep", "stl", "obj")


# ═══════════════════════════════════════════════════════════════════════════
# 5. ABAQUS Engine (requires Abaqus CAE on system)
# ═══════════════════════════════════════════════════════════════════════════

class ABAQUSEngine(EngineInterface):
    """Abaqus FEA software integration.

    Requires Abaqus CAE installed and its Python API accessible.
    Typically invoked via: abaqus python main.py --engine abaqus
    or by running this script inside Abaqus's Python interpreter.
    """

    def __init__(self):
        try:
            import abaqus
            import abaqusConstants
            import part
            import assembly
            import mesh as abq_mesh
            self._abaqus = True
        except ImportError:
            self._abaqus = False
            raise ImportError(
                "Abaqus Python API not found. Ensure:\n"
                "  1. Abaqus CAE is installed\n"
                "  2. Run with: abaqus python Python/demo/main.py\n"
                "  3. Or add Abaqus Python to PYTHONPATH"
            )

    def create_model(self, config: dict) -> MeshData:
        if not self._abaqus:
            raise RuntimeError("ABAQUS not available")
        raise NotImplementedError("ABAQUS adapter ready — implement model creation as needed")

    def export_model(self, mesh: MeshData, filepath: str, fmt: str = "inp") -> str:
        if not self._abaqus:
            raise RuntimeError("ABAQUS not available")
        raise NotImplementedError("Awaiting implementation")

    def supports_format(self, fmt: str) -> bool:
        return fmt.lower() in ("inp", "odb", "cae", "obj", "stl")


# ═══════════════════════════════════════════════════════════════════════════
# 6. AutoCAD Engine (via ezdxf — pure Python, already installed)
# ═══════════════════════════════════════════════════════════════════════════

class AutoCADEngine(EngineInterface):
    """AutoCAD integration via ezdxf (DXF format) and COM (when AutoCAD is running).

    Two modes:
      - ezdxf mode (default): creates DXF files without needing AutoCAD installed
      - COM mode: drives a running AutoCAD instance via pyautocad / win32com
    """

    def __init__(self, mode: str = "ezdxf"):
        self._mode = mode
        if mode == "ezdxf":
            import ezdxf
            self._ezdxf = ezdxf
        elif mode == "com":
            try:
                import win32com.client
                self._acad = win32com.client.Dispatch("AutoCAD.Application")
                self._com = True
            except (ImportError, Exception):
                self._com = False
                raise ImportError("AutoCAD COM not available. Install pywin32 + ensure AutoCAD is running.")

    def create_model(self, config: dict) -> MeshData:
        shape = config.get("shape", "sphere")
        resolution = config.get("resolution", 32)
        size = config.get("size", 1.0)

        if shape == "sphere":
            return self._make_sphere(resolution, size)
        elif shape in ("cube", "box"):
            return self._make_box(size)
        elif shape == "cylinder":
            return self._make_cylinder(resolution, size)
        else:
            return self._make_sphere(resolution, size)

    def _make_sphere(self, res: int, size: float) -> MeshData:
        import math
        verts, faces = [], []
        for i in range(res):
            phi = math.pi * i / (res - 1)
            for j in range(res):
                theta = 2 * math.pi * j / (res - 1)
                x = size * math.sin(phi) * math.cos(theta)
                y = size * math.sin(phi) * math.sin(theta)
                z = size * math.cos(phi)
                verts.append((x, y, z))
        for i in range(res - 1):
            for j in range(res - 1):
                a = i * res + j
                b = a + res
                faces.append((a, b, a + 1))
                faces.append((a + 1, b, b + 1))
        return MeshData(vertices=verts, faces=faces, name="sphere_dxf")

    def _make_box(self, size: float) -> MeshData:
        s = size / 2
        verts = [
            (-s, -s, -s), (s, -s, -s), (s, s, -s), (-s, s, -s),
            (-s, -s, s), (s, -s, s), (s, s, s), (-s, s, s),
        ]
        faces = [
            (0,1,2), (0,2,3), (4,5,6), (4,6,7), (0,1,5), (0,5,4),
            (2,3,7), (2,7,6), (1,2,6), (1,6,5), (0,3,7), (0,7,4),
        ]
        return MeshData(vertices=verts, faces=faces, name="box_dxf")

    def _make_cylinder(self, res: int, size: float) -> MeshData:
        import math
        r, h = size * 0.5, size
        verts, faces = [], []
        for j in range(res):
            theta = 2 * math.pi * j / res
            verts.append((r * math.cos(theta), r * math.sin(theta), -h / 2))
        for j in range(res):
            theta = 2 * math.pi * j / res
            verts.append((r * math.cos(theta), r * math.sin(theta), h / 2))
        for j in range(res):
            nxt = (j + 1) % res
            faces.append((j, nxt, res + j))
            faces.append((nxt, res + nxt, res + j))
        return MeshData(vertices=verts, faces=faces, name="cylinder_dxf")

    def export_model(self, mesh: MeshData, filepath: str, fmt: str = "dxf") -> str:
        filepath = filepath if filepath.endswith(f".{fmt}") else f"{filepath}.{fmt}"

        if self._mode == "ezdxf":
            doc = self._ezdxf.new()
            msp = doc.modelspace()

            builder = self._ezdxf.render.MeshBuilder()
            # ezdxf add_face expects actual vertex coords, not indices
            for f in mesh.faces:
                v0 = mesh.vertices[f[0]]
                v1 = mesh.vertices[f[1]]
                v2 = mesh.vertices[f[2]]
                builder.add_face([v0, v1, v2])
            builder.render_polyface(msp, dxfattribs={"layer": "ETU_MODEL"})
            doc.saveas(filepath)
        elif self._mode == "com":
            raise NotImplementedError("COM export not yet implemented")
        return filepath

    def supports_format(self, fmt: str) -> bool:
        return fmt.lower() in ("dxf", "obj", "stl")


# ═══════════════════════════════════════════════════════════════════════════
# 7. Engine registry & factory
# ═══════════════════════════════════════════════════════════════════════════

_ENGINE_REGISTRY: dict[str, Callable[[], EngineInterface]] = {
    "vtk":       lambda: VTKEngine(),
    "opencascade": lambda: OpenCASCADEEngine(),
    "occt":     lambda: OpenCASCADEEngine(),
    "abaqus":   lambda: ABAQUSEngine(),
    "ezdxf":    lambda: AutoCADEngine(mode="ezdxf"),
    "autocad":  lambda: AutoCADEngine(mode="ezdxf"),
}


def list_engines() -> list[EngineInfo]:
    """Discover which engines are available."""
    results = []
    for key, factory in _ENGINE_REGISTRY.items():
        try:
            engine = factory()
            notes = "ready"
        except ImportError as e:
            notes = str(e).split("\n")[0]
        except Exception as e:
            notes = str(e)
        results.append(EngineInfo(
            key=key,
            name=key.upper(),
            available="ready" in notes.lower() or "notimplemented" in notes.lower(),
            notes=notes,
        ))
    return results


def get_engine(name: str) -> EngineInterface:
    """Get an engine by name, falling back to VTK."""
    name = name.lower()
    if name in _ENGINE_REGISTRY:
        try:
            return _ENGINE_REGISTRY[name]()
        except ImportError:
            pass
    # fallback: try VTK
    print(f"[demo] Engine '{name}' not available; falling back to VTK")
    return VTKEngine()


# ═══════════════════════════════════════════════════════════════════════════
# 8. Step-motion video pipeline
# ═══════════════════════════════════════════════════════════════════════════

class StepMotionPipeline:
    """Generates multiple 3D models and composes a step-motion video."""

    def __init__(self, engine: EngineInterface, output_dir: str = "./output"):
        self.engine = engine
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def run(self, frames: int = 10, shape: str = "sphere",
            format: str = "obj", rotation_step: float = 36.0) -> list[str]:
        """Generate frames, export models, return file paths."""
        files = []
        print(f"[demo] Generating {frames} frames using engine: {type(self.engine).__name__}")
        for i in range(frames):
            rotation = i * rotation_step
            config = {
                "shape": shape,
                "resolution": 32,
                "size": 1.0 + 0.05 * i,  # slight size progression
                "rotation": rotation,
            }
            mesh = self.engine.create_model(config)
            fname = os.path.join(self.output_dir, f"frame_{i:04d}")
            exported = self.engine.export_model(mesh, fname, fmt=format)
            files.append(exported)
            print(f"[demo]   frame {i:04d} -> {exported}")
        return files


# ═══════════════════════════════════════════════════════════════════════════
# 9. Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="ETU Demo — step-motion 3D model generation",
    )
    parser.add_argument("--engine", default="vtk",
                        help="Engine: vtk, opencascade, abaqus, ezdxf/autocad")
    parser.add_argument("--frames", type=int, default=10,
                        help="Number of frames (default: 10)")
    parser.add_argument("--shape", default="sphere",
                        help="Shape: sphere, cube, cylinder, cone, torus")
    parser.add_argument("--format", default="obj",
                        help="Output format: obj, stl, dxf, step, inp")
    parser.add_argument("--output", default="./Python/demo/output",
                        help="Output directory")
    parser.add_argument("--list-engines", action="store_true",
                        help="Show available engines and exit")
    args = parser.parse_args()

    if args.list_engines:
        print("\nAvailable 3D Engines:")
        print("-" * 60)
        for info in list_engines():
            status = "✓" if info.available else "✗"
            print(f"  [{status}] {info.key:15s} {info.notes}")
        print("-" * 60)
        print("\nTo use an engine: python main.py --engine <name>")
        return

    engine = get_engine(args.engine)
    pipeline = StepMotionPipeline(engine, output_dir=args.output)
    files = pipeline.run(
        frames=args.frames,
        shape=args.shape,
        format=args.format,
    )
    print(f"\n[demo] Done! {len(files)} frames written to {args.output}")


if __name__ == "__main__":
    main()


 