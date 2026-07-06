
#ifndef VTKIOVPIC_EXPORT_H
#define VTKIOVPIC_EXPORT_H

#ifdef VTKIOVPIC_STATIC_DEFINE
#  define VTKIOVPIC_EXPORT
#  define VTKIOVPIC_NO_EXPORT
#else
#  ifndef VTKIOVPIC_EXPORT
#    ifdef IOVPIC_EXPORTS
        /* We are building this library */
#      define VTKIOVPIC_EXPORT __declspec(dllexport)
#    else
        /* We are using this library */
#      define VTKIOVPIC_EXPORT __declspec(dllimport)
#    endif
#  endif

#  ifndef VTKIOVPIC_NO_EXPORT
#    define VTKIOVPIC_NO_EXPORT 
#  endif
#endif

#ifndef VTKIOVPIC_DEPRECATED
#  define VTKIOVPIC_DEPRECATED __declspec(deprecated)
#endif

#ifndef VTKIOVPIC_DEPRECATED_EXPORT
#  define VTKIOVPIC_DEPRECATED_EXPORT VTKIOVPIC_EXPORT VTKIOVPIC_DEPRECATED
#endif

#ifndef VTKIOVPIC_DEPRECATED_NO_EXPORT
#  define VTKIOVPIC_DEPRECATED_NO_EXPORT VTKIOVPIC_NO_EXPORT VTKIOVPIC_DEPRECATED
#endif

/* NOLINTNEXTLINE(readability-avoid-unconditional-preprocessor-if) */
#if 0 /* DEFINE_NO_DEPRECATED */
#  ifndef VTKIOVPIC_NO_DEPRECATED
#    define VTKIOVPIC_NO_DEPRECATED
#  endif
#endif

/* VTK-HeaderTest-Exclude: vtkIOVPICModule.h */

/* Include ABI Namespace */
#include "vtkABINamespace.h"

#endif /* VTKIOVPIC_EXPORT_H */
