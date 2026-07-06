
#ifndef VTKRENDERINGMATPLOTLIB_EXPORT_H
#define VTKRENDERINGMATPLOTLIB_EXPORT_H

#ifdef VTKRENDERINGMATPLOTLIB_STATIC_DEFINE
#  define VTKRENDERINGMATPLOTLIB_EXPORT
#  define VTKRENDERINGMATPLOTLIB_NO_EXPORT
#else
#  ifndef VTKRENDERINGMATPLOTLIB_EXPORT
#    ifdef RenderingMatplotlib_EXPORTS
        /* We are building this library */
#      define VTKRENDERINGMATPLOTLIB_EXPORT __declspec(dllexport)
#    else
        /* We are using this library */
#      define VTKRENDERINGMATPLOTLIB_EXPORT __declspec(dllimport)
#    endif
#  endif

#  ifndef VTKRENDERINGMATPLOTLIB_NO_EXPORT
#    define VTKRENDERINGMATPLOTLIB_NO_EXPORT 
#  endif
#endif

#ifndef VTKRENDERINGMATPLOTLIB_DEPRECATED
#  define VTKRENDERINGMATPLOTLIB_DEPRECATED __declspec(deprecated)
#endif

#ifndef VTKRENDERINGMATPLOTLIB_DEPRECATED_EXPORT
#  define VTKRENDERINGMATPLOTLIB_DEPRECATED_EXPORT VTKRENDERINGMATPLOTLIB_EXPORT VTKRENDERINGMATPLOTLIB_DEPRECATED
#endif

#ifndef VTKRENDERINGMATPLOTLIB_DEPRECATED_NO_EXPORT
#  define VTKRENDERINGMATPLOTLIB_DEPRECATED_NO_EXPORT VTKRENDERINGMATPLOTLIB_NO_EXPORT VTKRENDERINGMATPLOTLIB_DEPRECATED
#endif

/* NOLINTNEXTLINE(readability-avoid-unconditional-preprocessor-if) */
#if 0 /* DEFINE_NO_DEPRECATED */
#  ifndef VTKRENDERINGMATPLOTLIB_NO_DEPRECATED
#    define VTKRENDERINGMATPLOTLIB_NO_DEPRECATED
#  endif
#endif

/* VTK-HeaderTest-Exclude: vtkRenderingMatplotlibModule.h */

/* Include ABI Namespace */
#include "vtkABINamespace.h"
/* AutoInit dependencies. */
#include "vtkRenderingFreeTypeModule.h"


/* AutoInit implementations. */
#ifdef vtkRenderingMatplotlib_AUTOINIT_INCLUDE
#include vtkRenderingMatplotlib_AUTOINIT_INCLUDE
#endif
#ifdef vtkRenderingMatplotlib_AUTOINIT
#include "vtkAutoInit.h"
VTK_MODULE_AUTOINIT(vtkRenderingMatplotlib)
#endif

#endif /* VTKRENDERINGMATPLOTLIB_EXPORT_H */
