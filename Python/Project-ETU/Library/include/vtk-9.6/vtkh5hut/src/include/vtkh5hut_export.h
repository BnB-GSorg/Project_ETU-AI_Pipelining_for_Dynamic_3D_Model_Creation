
#ifndef VTKH5HUT_EXPORT_H
#define VTKH5HUT_EXPORT_H

#ifdef H5HUT_STATIC_DEFINE
#  define VTKH5HUT_EXPORT
#  define H5HUT_NO_EXPORT
#else
#  ifndef VTKH5HUT_EXPORT
#    ifdef h5hut_EXPORTS
        /* We are building this library */
#      define VTKH5HUT_EXPORT __declspec(dllexport)
#    else
        /* We are using this library */
#      define VTKH5HUT_EXPORT __declspec(dllimport)
#    endif
#  endif

#  ifndef H5HUT_NO_EXPORT
#    define H5HUT_NO_EXPORT 
#  endif
#endif

#ifndef H5HUT_DEPRECATED
#  define H5HUT_DEPRECATED __declspec(deprecated)
#endif

#ifndef H5HUT_DEPRECATED_EXPORT
#  define H5HUT_DEPRECATED_EXPORT VTKH5HUT_EXPORT H5HUT_DEPRECATED
#endif

#ifndef H5HUT_DEPRECATED_NO_EXPORT
#  define H5HUT_DEPRECATED_NO_EXPORT H5HUT_NO_EXPORT H5HUT_DEPRECATED
#endif

/* NOLINTNEXTLINE(readability-avoid-unconditional-preprocessor-if) */
#if 0 /* DEFINE_NO_DEPRECATED */
#  ifndef H5HUT_NO_DEPRECATED
#    define H5HUT_NO_DEPRECATED
#  endif
#endif

#endif /* VTKH5HUT_EXPORT_H */
