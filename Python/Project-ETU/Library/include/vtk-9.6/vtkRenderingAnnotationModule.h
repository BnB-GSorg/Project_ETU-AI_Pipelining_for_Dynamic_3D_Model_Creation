
#ifndef VTKRENDERINGANNOTATION_EXPORT_H
#define VTKRENDERINGANNOTATION_EXPORT_H

#ifdef VTKRENDERINGANNOTATION_STATIC_DEFINE
#  define VTKRENDERINGANNOTATION_EXPORT
#  define VTKRENDERINGANNOTATION_NO_EXPORT
#else
#  ifndef VTKRENDERINGANNOTATION_EXPORT
#    ifdef RenderingAnnotation_EXPORTS
        /* We are building this library */
#      define VTKRENDERINGANNOTATION_EXPORT __declspec(dllexport)
#    else
        /* We are using this library */
#      define VTKRENDERINGANNOTATION_EXPORT __declspec(dllimport)
#    endif
#  endif

#  ifndef VTKRENDERINGANNOTATION_NO_EXPORT
#    define VTKRENDERINGANNOTATION_NO_EXPORT 
#  endif
#endif

#ifndef VTKRENDERINGANNOTATION_DEPRECATED
#  define VTKRENDERINGANNOTATION_DEPRECATED __declspec(deprecated)
#endif

#ifndef VTKRENDERINGANNOTATION_DEPRECATED_EXPORT
#  define VTKRENDERINGANNOTATION_DEPRECATED_EXPORT VTKRENDERINGANNOTATION_EXPORT VTKRENDERINGANNOTATION_DEPRECATED
#endif

#ifndef VTKRENDERINGANNOTATION_DEPRECATED_NO_EXPORT
#  define VTKRENDERINGANNOTATION_DEPRECATED_NO_EXPORT VTKRENDERINGANNOTATION_NO_EXPORT VTKRENDERINGANNOTATION_DEPRECATED
#endif

/* NOLINTNEXTLINE(readability-avoid-unconditional-preprocessor-if) */
#if 0 /* DEFINE_NO_DEPRECATED */
#  ifndef VTKRENDERINGANNOTATION_NO_DEPRECATED
#    define VTKRENDERINGANNOTATION_NO_DEPRECATED
#  endif
#endif

/* VTK-HeaderTest-Exclude: vtkRenderingAnnotationModule.h */

/* Include ABI Namespace */
#include "vtkABINamespace.h"

VTK_ABI_NAMESPACE_BEGIN
VTKRENDERINGANNOTATION_EXPORT void AddRegistrar_vtkRenderingAnnotation();
VTK_ABI_NAMESPACE_END
namespace
{
  struct vtkRenderingAnnotation_SerDesRegistrar
  {
    vtkRenderingAnnotation_SerDesRegistrar()
    {
      AddRegistrar_vtkRenderingAnnotation();
    }
  } vtkRenderingAnnotation_SerDesRegistrar_Instance;
}

#endif /* VTKRENDERINGANNOTATION_EXPORT_H */
