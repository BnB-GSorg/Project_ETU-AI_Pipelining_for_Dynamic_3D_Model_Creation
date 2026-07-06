
#ifndef VTKWEBGLEXPORTER_EXPORT_H
#define VTKWEBGLEXPORTER_EXPORT_H

#ifdef VTKWEBGLEXPORTER_STATIC_DEFINE
#  define VTKWEBGLEXPORTER_EXPORT
#  define VTKWEBGLEXPORTER_NO_EXPORT
#else
#  ifndef VTKWEBGLEXPORTER_EXPORT
#    ifdef WebGLExporter_EXPORTS
        /* We are building this library */
#      define VTKWEBGLEXPORTER_EXPORT __declspec(dllexport)
#    else
        /* We are using this library */
#      define VTKWEBGLEXPORTER_EXPORT __declspec(dllimport)
#    endif
#  endif

#  ifndef VTKWEBGLEXPORTER_NO_EXPORT
#    define VTKWEBGLEXPORTER_NO_EXPORT 
#  endif
#endif

#ifndef VTKWEBGLEXPORTER_DEPRECATED
#  define VTKWEBGLEXPORTER_DEPRECATED __declspec(deprecated)
#endif

#ifndef VTKWEBGLEXPORTER_DEPRECATED_EXPORT
#  define VTKWEBGLEXPORTER_DEPRECATED_EXPORT VTKWEBGLEXPORTER_EXPORT VTKWEBGLEXPORTER_DEPRECATED
#endif

#ifndef VTKWEBGLEXPORTER_DEPRECATED_NO_EXPORT
#  define VTKWEBGLEXPORTER_DEPRECATED_NO_EXPORT VTKWEBGLEXPORTER_NO_EXPORT VTKWEBGLEXPORTER_DEPRECATED
#endif

/* NOLINTNEXTLINE(readability-avoid-unconditional-preprocessor-if) */
#if 0 /* DEFINE_NO_DEPRECATED */
#  ifndef VTKWEBGLEXPORTER_NO_DEPRECATED
#    define VTKWEBGLEXPORTER_NO_DEPRECATED
#  endif
#endif

/* VTK-HeaderTest-Exclude: vtkWebGLExporterModule.h */

/* Include ABI Namespace */
#include "vtkABINamespace.h"

#endif /* VTKWEBGLEXPORTER_EXPORT_H */
