
#ifndef VTKWEBCORE_EXPORT_H
#define VTKWEBCORE_EXPORT_H

#ifdef VTKWEBCORE_STATIC_DEFINE
#  define VTKWEBCORE_EXPORT
#  define VTKWEBCORE_NO_EXPORT
#else
#  ifndef VTKWEBCORE_EXPORT
#    ifdef WebCore_EXPORTS
        /* We are building this library */
#      define VTKWEBCORE_EXPORT __declspec(dllexport)
#    else
        /* We are using this library */
#      define VTKWEBCORE_EXPORT __declspec(dllimport)
#    endif
#  endif

#  ifndef VTKWEBCORE_NO_EXPORT
#    define VTKWEBCORE_NO_EXPORT 
#  endif
#endif

#ifndef VTKWEBCORE_DEPRECATED
#  define VTKWEBCORE_DEPRECATED __declspec(deprecated)
#endif

#ifndef VTKWEBCORE_DEPRECATED_EXPORT
#  define VTKWEBCORE_DEPRECATED_EXPORT VTKWEBCORE_EXPORT VTKWEBCORE_DEPRECATED
#endif

#ifndef VTKWEBCORE_DEPRECATED_NO_EXPORT
#  define VTKWEBCORE_DEPRECATED_NO_EXPORT VTKWEBCORE_NO_EXPORT VTKWEBCORE_DEPRECATED
#endif

/* NOLINTNEXTLINE(readability-avoid-unconditional-preprocessor-if) */
#if 0 /* DEFINE_NO_DEPRECATED */
#  ifndef VTKWEBCORE_NO_DEPRECATED
#    define VTKWEBCORE_NO_DEPRECATED
#  endif
#endif

/* VTK-HeaderTest-Exclude: vtkWebCoreModule.h */

/* Include ABI Namespace */
#include "vtkABINamespace.h"

#endif /* VTKWEBCORE_EXPORT_H */
