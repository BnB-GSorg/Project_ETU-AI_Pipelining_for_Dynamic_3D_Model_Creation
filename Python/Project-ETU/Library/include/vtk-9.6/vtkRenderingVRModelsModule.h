
#ifndef VTKRENDERINGVRMODELS_EXPORT_H
#define VTKRENDERINGVRMODELS_EXPORT_H

#ifdef VTKRENDERINGVRMODELS_STATIC_DEFINE
#  define VTKRENDERINGVRMODELS_EXPORT
#  define VTKRENDERINGVRMODELS_NO_EXPORT
#else
#  ifndef VTKRENDERINGVRMODELS_EXPORT
#    ifdef RenderingVRModels_EXPORTS
        /* We are building this library */
#      define VTKRENDERINGVRMODELS_EXPORT __declspec(dllexport)
#    else
        /* We are using this library */
#      define VTKRENDERINGVRMODELS_EXPORT __declspec(dllimport)
#    endif
#  endif

#  ifndef VTKRENDERINGVRMODELS_NO_EXPORT
#    define VTKRENDERINGVRMODELS_NO_EXPORT 
#  endif
#endif

#ifndef VTKRENDERINGVRMODELS_DEPRECATED
#  define VTKRENDERINGVRMODELS_DEPRECATED __declspec(deprecated)
#endif

#ifndef VTKRENDERINGVRMODELS_DEPRECATED_EXPORT
#  define VTKRENDERINGVRMODELS_DEPRECATED_EXPORT VTKRENDERINGVRMODELS_EXPORT VTKRENDERINGVRMODELS_DEPRECATED
#endif

#ifndef VTKRENDERINGVRMODELS_DEPRECATED_NO_EXPORT
#  define VTKRENDERINGVRMODELS_DEPRECATED_NO_EXPORT VTKRENDERINGVRMODELS_NO_EXPORT VTKRENDERINGVRMODELS_DEPRECATED
#endif

/* NOLINTNEXTLINE(readability-avoid-unconditional-preprocessor-if) */
#if 0 /* DEFINE_NO_DEPRECATED */
#  ifndef VTKRENDERINGVRMODELS_NO_DEPRECATED
#    define VTKRENDERINGVRMODELS_NO_DEPRECATED
#  endif
#endif

/* VTK-HeaderTest-Exclude: vtkRenderingVRModelsModule.h */

/* Include ABI Namespace */
#include "vtkABINamespace.h"
/* AutoInit dependencies. */
#include "vtkRenderingCoreModule.h"
#include "vtkRenderingOpenGL2Module.h"


/* AutoInit implementations. */
#ifdef vtkRenderingVRModels_AUTOINIT_INCLUDE
#include vtkRenderingVRModels_AUTOINIT_INCLUDE
#endif
#ifdef vtkRenderingVRModels_AUTOINIT
#include "vtkAutoInit.h"
VTK_MODULE_AUTOINIT(vtkRenderingVRModels)
#endif

#endif /* VTKRENDERINGVRMODELS_EXPORT_H */
