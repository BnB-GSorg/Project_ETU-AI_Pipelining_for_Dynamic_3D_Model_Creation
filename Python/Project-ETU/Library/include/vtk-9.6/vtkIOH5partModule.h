
#ifndef VTKIOH5PART_EXPORT_H
#define VTKIOH5PART_EXPORT_H

#ifdef VTKIOH5PART_STATIC_DEFINE
#  define VTKIOH5PART_EXPORT
#  define VTKIOH5PART_NO_EXPORT
#else
#  ifndef VTKIOH5PART_EXPORT
#    ifdef IOH5part_EXPORTS
        /* We are building this library */
#      define VTKIOH5PART_EXPORT __declspec(dllexport)
#    else
        /* We are using this library */
#      define VTKIOH5PART_EXPORT __declspec(dllimport)
#    endif
#  endif

#  ifndef VTKIOH5PART_NO_EXPORT
#    define VTKIOH5PART_NO_EXPORT 
#  endif
#endif

#ifndef VTKIOH5PART_DEPRECATED
#  define VTKIOH5PART_DEPRECATED __declspec(deprecated)
#endif

#ifndef VTKIOH5PART_DEPRECATED_EXPORT
#  define VTKIOH5PART_DEPRECATED_EXPORT VTKIOH5PART_EXPORT VTKIOH5PART_DEPRECATED
#endif

#ifndef VTKIOH5PART_DEPRECATED_NO_EXPORT
#  define VTKIOH5PART_DEPRECATED_NO_EXPORT VTKIOH5PART_NO_EXPORT VTKIOH5PART_DEPRECATED
#endif

/* NOLINTNEXTLINE(readability-avoid-unconditional-preprocessor-if) */
#if 0 /* DEFINE_NO_DEPRECATED */
#  ifndef VTKIOH5PART_NO_DEPRECATED
#    define VTKIOH5PART_NO_DEPRECATED
#  endif
#endif

/* VTK-HeaderTest-Exclude: vtkIOH5partModule.h */

/* Include ABI Namespace */
#include "vtkABINamespace.h"

#endif /* VTKIOH5PART_EXPORT_H */
