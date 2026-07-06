
#ifndef VTKIOXDMF2_EXPORT_H
#define VTKIOXDMF2_EXPORT_H

#ifdef VTKIOXDMF2_STATIC_DEFINE
#  define VTKIOXDMF2_EXPORT
#  define VTKIOXDMF2_NO_EXPORT
#else
#  ifndef VTKIOXDMF2_EXPORT
#    ifdef IOXdmf2_EXPORTS
        /* We are building this library */
#      define VTKIOXDMF2_EXPORT __declspec(dllexport)
#    else
        /* We are using this library */
#      define VTKIOXDMF2_EXPORT __declspec(dllimport)
#    endif
#  endif

#  ifndef VTKIOXDMF2_NO_EXPORT
#    define VTKIOXDMF2_NO_EXPORT 
#  endif
#endif

#ifndef VTKIOXDMF2_DEPRECATED
#  define VTKIOXDMF2_DEPRECATED __declspec(deprecated)
#endif

#ifndef VTKIOXDMF2_DEPRECATED_EXPORT
#  define VTKIOXDMF2_DEPRECATED_EXPORT VTKIOXDMF2_EXPORT VTKIOXDMF2_DEPRECATED
#endif

#ifndef VTKIOXDMF2_DEPRECATED_NO_EXPORT
#  define VTKIOXDMF2_DEPRECATED_NO_EXPORT VTKIOXDMF2_NO_EXPORT VTKIOXDMF2_DEPRECATED
#endif

/* NOLINTNEXTLINE(readability-avoid-unconditional-preprocessor-if) */
#if 0 /* DEFINE_NO_DEPRECATED */
#  ifndef VTKIOXDMF2_NO_DEPRECATED
#    define VTKIOXDMF2_NO_DEPRECATED
#  endif
#endif

/* VTK-HeaderTest-Exclude: vtkIOXdmf2Module.h */

/* Include ABI Namespace */
#include "vtkABINamespace.h"

#endif /* VTKIOXDMF2_EXPORT_H */
