
#ifndef VTKRENDERINGVOLUME_EXPORT_H
#define VTKRENDERINGVOLUME_EXPORT_H

#ifdef VTKRENDERINGVOLUME_STATIC_DEFINE
#  define VTKRENDERINGVOLUME_EXPORT
#  define VTKRENDERINGVOLUME_NO_EXPORT
#else
#  ifndef VTKRENDERINGVOLUME_EXPORT
#    ifdef RenderingVolume_EXPORTS
        /* We are building this library */
#      define VTKRENDERINGVOLUME_EXPORT __declspec(dllexport)
#    else
        /* We are using this library */
#      define VTKRENDERINGVOLUME_EXPORT __declspec(dllimport)
#    endif
#  endif

#  ifndef VTKRENDERINGVOLUME_NO_EXPORT
#    define VTKRENDERINGVOLUME_NO_EXPORT 
#  endif
#endif

#ifndef VTKRENDERINGVOLUME_DEPRECATED
#  define VTKRENDERINGVOLUME_DEPRECATED __declspec(deprecated)
#endif

#ifndef VTKRENDERINGVOLUME_DEPRECATED_EXPORT
#  define VTKRENDERINGVOLUME_DEPRECATED_EXPORT VTKRENDERINGVOLUME_EXPORT VTKRENDERINGVOLUME_DEPRECATED
#endif

#ifndef VTKRENDERINGVOLUME_DEPRECATED_NO_EXPORT
#  define VTKRENDERINGVOLUME_DEPRECATED_NO_EXPORT VTKRENDERINGVOLUME_NO_EXPORT VTKRENDERINGVOLUME_DEPRECATED
#endif

/* NOLINTNEXTLINE(readability-avoid-unconditional-preprocessor-if) */
#if 0 /* DEFINE_NO_DEPRECATED */
#  ifndef VTKRENDERINGVOLUME_NO_DEPRECATED
#    define VTKRENDERINGVOLUME_NO_DEPRECATED
#  endif
#endif

/* VTK-HeaderTest-Exclude: vtkRenderingVolumeModule.h */

/* Include ABI Namespace */
#include "vtkABINamespace.h"
/* AutoInit dependencies. */
#include "vtkRenderingCoreModule.h"


/* AutoInit implementations. */
#ifdef vtkRenderingVolume_AUTOINIT_INCLUDE
#include vtkRenderingVolume_AUTOINIT_INCLUDE
#endif
#ifdef vtkRenderingVolume_AUTOINIT
#include "vtkAutoInit.h"
VTK_MODULE_AUTOINIT(vtkRenderingVolume)
#endif

VTK_ABI_NAMESPACE_BEGIN
VTKRENDERINGVOLUME_EXPORT void AddRegistrar_vtkRenderingVolume();
VTK_ABI_NAMESPACE_END
namespace
{
  struct vtkRenderingVolume_SerDesRegistrar
  {
    vtkRenderingVolume_SerDesRegistrar()
    {
      AddRegistrar_vtkRenderingVolume();
    }
  } vtkRenderingVolume_SerDesRegistrar_Instance;
}

#endif /* VTKRENDERINGVOLUME_EXPORT_H */
