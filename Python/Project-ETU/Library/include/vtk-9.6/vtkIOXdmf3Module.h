
#ifndef VTKIOXDMF3_EXPORT_H
#define VTKIOXDMF3_EXPORT_H

#ifdef VTKIOXDMF3_STATIC_DEFINE
#  define VTKIOXDMF3_EXPORT
#  define VTKIOXDMF3_NO_EXPORT
#else
#  ifndef VTKIOXDMF3_EXPORT
#    ifdef IOXdmf3_EXPORTS
        /* We are building this library */
#      define VTKIOXDMF3_EXPORT __declspec(dllexport)
#    else
        /* We are using this library */
#      define VTKIOXDMF3_EXPORT __declspec(dllimport)
#    endif
#  endif

#  ifndef VTKIOXDMF3_NO_EXPORT
#    define VTKIOXDMF3_NO_EXPORT 
#  endif
#endif

#ifndef VTKIOXDMF3_DEPRECATED
#  define VTKIOXDMF3_DEPRECATED __declspec(deprecated)
#endif

#ifndef VTKIOXDMF3_DEPRECATED_EXPORT
#  define VTKIOXDMF3_DEPRECATED_EXPORT VTKIOXDMF3_EXPORT VTKIOXDMF3_DEPRECATED
#endif

#ifndef VTKIOXDMF3_DEPRECATED_NO_EXPORT
#  define VTKIOXDMF3_DEPRECATED_NO_EXPORT VTKIOXDMF3_NO_EXPORT VTKIOXDMF3_DEPRECATED
#endif

/* NOLINTNEXTLINE(readability-avoid-unconditional-preprocessor-if) */
#if 0 /* DEFINE_NO_DEPRECATED */
#  ifndef VTKIOXDMF3_NO_DEPRECATED
#    define VTKIOXDMF3_NO_DEPRECATED
#  endif
#endif

/* VTK-HeaderTest-Exclude: vtkIOXdmf3Module.h */

/* Include ABI Namespace */
#include "vtkABINamespace.h"

/* AutoInit implementations. */
#ifdef vtkIOXdmf3_AUTOINIT_INCLUDE
#include vtkIOXdmf3_AUTOINIT_INCLUDE
#endif
#ifdef vtkIOXdmf3_AUTOINIT
#include "vtkAutoInit.h"
VTK_MODULE_AUTOINIT(vtkIOXdmf3)
#endif

#endif /* VTKIOXDMF3_EXPORT_H */
