
#ifndef VTKCOMMONPYTHON_EXPORT_H
#define VTKCOMMONPYTHON_EXPORT_H

#ifdef VTKCOMMONPYTHON_STATIC_DEFINE
#  define VTKCOMMONPYTHON_EXPORT
#  define VTKCOMMONPYTHON_NO_EXPORT
#else
#  ifndef VTKCOMMONPYTHON_EXPORT
#    ifdef CommonPython_EXPORTS
        /* We are building this library */
#      define VTKCOMMONPYTHON_EXPORT __declspec(dllexport)
#    else
        /* We are using this library */
#      define VTKCOMMONPYTHON_EXPORT __declspec(dllimport)
#    endif
#  endif

#  ifndef VTKCOMMONPYTHON_NO_EXPORT
#    define VTKCOMMONPYTHON_NO_EXPORT 
#  endif
#endif

#ifndef VTKCOMMONPYTHON_DEPRECATED
#  define VTKCOMMONPYTHON_DEPRECATED __declspec(deprecated)
#endif

#ifndef VTKCOMMONPYTHON_DEPRECATED_EXPORT
#  define VTKCOMMONPYTHON_DEPRECATED_EXPORT VTKCOMMONPYTHON_EXPORT VTKCOMMONPYTHON_DEPRECATED
#endif

#ifndef VTKCOMMONPYTHON_DEPRECATED_NO_EXPORT
#  define VTKCOMMONPYTHON_DEPRECATED_NO_EXPORT VTKCOMMONPYTHON_NO_EXPORT VTKCOMMONPYTHON_DEPRECATED
#endif

/* NOLINTNEXTLINE(readability-avoid-unconditional-preprocessor-if) */
#if 0 /* DEFINE_NO_DEPRECATED */
#  ifndef VTKCOMMONPYTHON_NO_DEPRECATED
#    define VTKCOMMONPYTHON_NO_DEPRECATED
#  endif
#endif

/* VTK-HeaderTest-Exclude: vtkCommonPythonModule.h */

/* Include ABI Namespace */
#include "vtkABINamespace.h"

#endif /* VTKCOMMONPYTHON_EXPORT_H */
