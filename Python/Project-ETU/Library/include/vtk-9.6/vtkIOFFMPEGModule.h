
#ifndef VTKIOFFMPEG_EXPORT_H
#define VTKIOFFMPEG_EXPORT_H

#ifdef VTKIOFFMPEG_STATIC_DEFINE
#  define VTKIOFFMPEG_EXPORT
#  define VTKIOFFMPEG_NO_EXPORT
#else
#  ifndef VTKIOFFMPEG_EXPORT
#    ifdef IOFFMPEG_EXPORTS
        /* We are building this library */
#      define VTKIOFFMPEG_EXPORT __declspec(dllexport)
#    else
        /* We are using this library */
#      define VTKIOFFMPEG_EXPORT __declspec(dllimport)
#    endif
#  endif

#  ifndef VTKIOFFMPEG_NO_EXPORT
#    define VTKIOFFMPEG_NO_EXPORT 
#  endif
#endif

#ifndef VTKIOFFMPEG_DEPRECATED
#  define VTKIOFFMPEG_DEPRECATED __declspec(deprecated)
#endif

#ifndef VTKIOFFMPEG_DEPRECATED_EXPORT
#  define VTKIOFFMPEG_DEPRECATED_EXPORT VTKIOFFMPEG_EXPORT VTKIOFFMPEG_DEPRECATED
#endif

#ifndef VTKIOFFMPEG_DEPRECATED_NO_EXPORT
#  define VTKIOFFMPEG_DEPRECATED_NO_EXPORT VTKIOFFMPEG_NO_EXPORT VTKIOFFMPEG_DEPRECATED
#endif

/* NOLINTNEXTLINE(readability-avoid-unconditional-preprocessor-if) */
#if 0 /* DEFINE_NO_DEPRECATED */
#  ifndef VTKIOFFMPEG_NO_DEPRECATED
#    define VTKIOFFMPEG_NO_DEPRECATED
#  endif
#endif

/* VTK-HeaderTest-Exclude: vtkIOFFMPEGModule.h */

/* Include ABI Namespace */
#include "vtkABINamespace.h"

#endif /* VTKIOFFMPEG_EXPORT_H */
