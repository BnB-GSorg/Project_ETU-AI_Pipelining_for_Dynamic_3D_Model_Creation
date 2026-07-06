
#ifndef VTKCOMMONCORE_EXPORT_H
#define VTKCOMMONCORE_EXPORT_H

#ifdef VTKCOMMONCORE_STATIC_DEFINE
#  define VTKCOMMONCORE_EXPORT
#  define VTKCOMMONCORE_NO_EXPORT
#else
#  ifndef VTKCOMMONCORE_EXPORT
#    ifdef CommonCore_EXPORTS
        /* We are building this library */
#      define VTKCOMMONCORE_EXPORT __declspec(dllexport)
#    else
        /* We are using this library */
#      define VTKCOMMONCORE_EXPORT __declspec(dllimport)
#    endif
#  endif

#  ifndef VTKCOMMONCORE_NO_EXPORT
#    define VTKCOMMONCORE_NO_EXPORT 
#  endif
#endif

#ifndef VTKCOMMONCORE_DEPRECATED
#  define VTKCOMMONCORE_DEPRECATED __declspec(deprecated)
#endif

#ifndef VTKCOMMONCORE_DEPRECATED_EXPORT
#  define VTKCOMMONCORE_DEPRECATED_EXPORT VTKCOMMONCORE_EXPORT VTKCOMMONCORE_DEPRECATED
#endif

#ifndef VTKCOMMONCORE_DEPRECATED_NO_EXPORT
#  define VTKCOMMONCORE_DEPRECATED_NO_EXPORT VTKCOMMONCORE_NO_EXPORT VTKCOMMONCORE_DEPRECATED
#endif

/* NOLINTNEXTLINE(readability-avoid-unconditional-preprocessor-if) */
#if 0 /* DEFINE_NO_DEPRECATED */
#  ifndef VTKCOMMONCORE_NO_DEPRECATED
#    define VTKCOMMONCORE_NO_DEPRECATED
#  endif
#endif

/* VTK-HeaderTest-Exclude: vtkCommonCoreModule.h */

/* Include ABI Namespace */
#include "vtkABINamespace.h"

VTK_ABI_NAMESPACE_BEGIN
VTKCOMMONCORE_EXPORT void AddRegistrar_vtkCommonCore();
VTK_ABI_NAMESPACE_END
namespace
{
  struct vtkCommonCore_SerDesRegistrar
  {
    vtkCommonCore_SerDesRegistrar()
    {
      AddRegistrar_vtkCommonCore();
    }
  } vtkCommonCore_SerDesRegistrar_Instance;
}

#endif /* VTKCOMMONCORE_EXPORT_H */
