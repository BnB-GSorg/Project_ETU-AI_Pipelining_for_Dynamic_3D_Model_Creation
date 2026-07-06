
#ifndef VTKVIEWSCONTEXT2D_EXPORT_H
#define VTKVIEWSCONTEXT2D_EXPORT_H

#ifdef VTKVIEWSCONTEXT2D_STATIC_DEFINE
#  define VTKVIEWSCONTEXT2D_EXPORT
#  define VTKVIEWSCONTEXT2D_NO_EXPORT
#else
#  ifndef VTKVIEWSCONTEXT2D_EXPORT
#    ifdef ViewsContext2D_EXPORTS
        /* We are building this library */
#      define VTKVIEWSCONTEXT2D_EXPORT __declspec(dllexport)
#    else
        /* We are using this library */
#      define VTKVIEWSCONTEXT2D_EXPORT __declspec(dllimport)
#    endif
#  endif

#  ifndef VTKVIEWSCONTEXT2D_NO_EXPORT
#    define VTKVIEWSCONTEXT2D_NO_EXPORT 
#  endif
#endif

#ifndef VTKVIEWSCONTEXT2D_DEPRECATED
#  define VTKVIEWSCONTEXT2D_DEPRECATED __declspec(deprecated)
#endif

#ifndef VTKVIEWSCONTEXT2D_DEPRECATED_EXPORT
#  define VTKVIEWSCONTEXT2D_DEPRECATED_EXPORT VTKVIEWSCONTEXT2D_EXPORT VTKVIEWSCONTEXT2D_DEPRECATED
#endif

#ifndef VTKVIEWSCONTEXT2D_DEPRECATED_NO_EXPORT
#  define VTKVIEWSCONTEXT2D_DEPRECATED_NO_EXPORT VTKVIEWSCONTEXT2D_NO_EXPORT VTKVIEWSCONTEXT2D_DEPRECATED
#endif

/* NOLINTNEXTLINE(readability-avoid-unconditional-preprocessor-if) */
#if 0 /* DEFINE_NO_DEPRECATED */
#  ifndef VTKVIEWSCONTEXT2D_NO_DEPRECATED
#    define VTKVIEWSCONTEXT2D_NO_DEPRECATED
#  endif
#endif

/* VTK-HeaderTest-Exclude: vtkViewsContext2DModule.h */

/* Include ABI Namespace */
#include "vtkABINamespace.h"

VTK_ABI_NAMESPACE_BEGIN
VTKVIEWSCONTEXT2D_EXPORT void AddRegistrar_vtkViewsContext2D();
VTK_ABI_NAMESPACE_END
namespace
{
  struct vtkViewsContext2D_SerDesRegistrar
  {
    vtkViewsContext2D_SerDesRegistrar()
    {
      AddRegistrar_vtkViewsContext2D();
    }
  } vtkViewsContext2D_SerDesRegistrar_Instance;
}

#endif /* VTKVIEWSCONTEXT2D_EXPORT_H */
