
#ifndef VTKIOPIO_EXPORT_H
#define VTKIOPIO_EXPORT_H

#ifdef VTKIOPIO_STATIC_DEFINE
#  define VTKIOPIO_EXPORT
#  define VTKIOPIO_NO_EXPORT
#else
#  ifndef VTKIOPIO_EXPORT
#    ifdef IOPIO_EXPORTS
        /* We are building this library */
#      define VTKIOPIO_EXPORT __declspec(dllexport)
#    else
        /* We are using this library */
#      define VTKIOPIO_EXPORT __declspec(dllimport)
#    endif
#  endif

#  ifndef VTKIOPIO_NO_EXPORT
#    define VTKIOPIO_NO_EXPORT 
#  endif
#endif

#ifndef VTKIOPIO_DEPRECATED
#  define VTKIOPIO_DEPRECATED __declspec(deprecated)
#endif

#ifndef VTKIOPIO_DEPRECATED_EXPORT
#  define VTKIOPIO_DEPRECATED_EXPORT VTKIOPIO_EXPORT VTKIOPIO_DEPRECATED
#endif

#ifndef VTKIOPIO_DEPRECATED_NO_EXPORT
#  define VTKIOPIO_DEPRECATED_NO_EXPORT VTKIOPIO_NO_EXPORT VTKIOPIO_DEPRECATED
#endif

/* NOLINTNEXTLINE(readability-avoid-unconditional-preprocessor-if) */
#if 0 /* DEFINE_NO_DEPRECATED */
#  ifndef VTKIOPIO_NO_DEPRECATED
#    define VTKIOPIO_NO_DEPRECATED
#  endif
#endif

/* VTK-HeaderTest-Exclude: vtkIOPIOModule.h */

/* Include ABI Namespace */
#include "vtkABINamespace.h"

#endif /* VTKIOPIO_EXPORT_H */
