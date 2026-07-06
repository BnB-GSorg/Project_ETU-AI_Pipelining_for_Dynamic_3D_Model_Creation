
#ifndef VTKIOAVMESH_EXPORT_H
#define VTKIOAVMESH_EXPORT_H

#ifdef VTKIOAVMESH_STATIC_DEFINE
#  define VTKIOAVMESH_EXPORT
#  define VTKIOAVMESH_NO_EXPORT
#else
#  ifndef VTKIOAVMESH_EXPORT
#    ifdef IOAvmesh_EXPORTS
        /* We are building this library */
#      define VTKIOAVMESH_EXPORT __declspec(dllexport)
#    else
        /* We are using this library */
#      define VTKIOAVMESH_EXPORT __declspec(dllimport)
#    endif
#  endif

#  ifndef VTKIOAVMESH_NO_EXPORT
#    define VTKIOAVMESH_NO_EXPORT 
#  endif
#endif

#ifndef VTKIOAVMESH_DEPRECATED
#  define VTKIOAVMESH_DEPRECATED __declspec(deprecated)
#endif

#ifndef VTKIOAVMESH_DEPRECATED_EXPORT
#  define VTKIOAVMESH_DEPRECATED_EXPORT VTKIOAVMESH_EXPORT VTKIOAVMESH_DEPRECATED
#endif

#ifndef VTKIOAVMESH_DEPRECATED_NO_EXPORT
#  define VTKIOAVMESH_DEPRECATED_NO_EXPORT VTKIOAVMESH_NO_EXPORT VTKIOAVMESH_DEPRECATED
#endif

/* NOLINTNEXTLINE(readability-avoid-unconditional-preprocessor-if) */
#if 0 /* DEFINE_NO_DEPRECATED */
#  ifndef VTKIOAVMESH_NO_DEPRECATED
#    define VTKIOAVMESH_NO_DEPRECATED
#  endif
#endif

/* VTK-HeaderTest-Exclude: vtkIOAvmeshModule.h */

/* Include ABI Namespace */
#include "vtkABINamespace.h"

#endif /* VTKIOAVMESH_EXPORT_H */
