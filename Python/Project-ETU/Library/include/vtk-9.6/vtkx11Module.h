
#ifndef VTKX11_EXPORT_H
#define VTKX11_EXPORT_H

#ifdef VTKX11_STATIC_DEFINE
#  define VTKX11_EXPORT
#  define VTKX11_NO_EXPORT
#else
#  ifndef VTKX11_EXPORT
#    ifdef x11_EXPORTS
        /* We are building this library */
#      define VTKX11_EXPORT __declspec(dllexport)
#    else
        /* We are using this library */
#      define VTKX11_EXPORT __declspec(dllimport)
#    endif
#  endif

#  ifndef VTKX11_NO_EXPORT
#    define VTKX11_NO_EXPORT 
#  endif
#endif

#ifndef VTKX11_DEPRECATED
#  define VTKX11_DEPRECATED __declspec(deprecated)
#endif

#ifndef VTKX11_DEPRECATED_EXPORT
#  define VTKX11_DEPRECATED_EXPORT VTKX11_EXPORT VTKX11_DEPRECATED
#endif

#ifndef VTKX11_DEPRECATED_NO_EXPORT
#  define VTKX11_DEPRECATED_NO_EXPORT VTKX11_NO_EXPORT VTKX11_DEPRECATED
#endif

/* NOLINTNEXTLINE(readability-avoid-unconditional-preprocessor-if) */
#if 0 /* DEFINE_NO_DEPRECATED */
#  ifndef VTKX11_NO_DEPRECATED
#    define VTKX11_NO_DEPRECATED
#  endif
#endif

/* VTK-HeaderTest-Exclude: vtkx11Module.h */

/* Include ABI Namespace */
#include "vtkABINamespace.h"

#endif /* VTKX11_EXPORT_H */
