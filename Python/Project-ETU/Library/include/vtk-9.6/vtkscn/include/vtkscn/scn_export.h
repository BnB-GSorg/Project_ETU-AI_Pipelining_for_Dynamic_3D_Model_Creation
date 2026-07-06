
#ifndef SCN_EXPORT_H
#define SCN_EXPORT_H

#ifdef SCN_STATIC_DEFINE
#  define SCN_EXPORT
#  define SCN_NO_EXPORT
#else
#  ifndef SCN_EXPORT
#    ifdef scn_EXPORTS
        /* We are building this library */
#      define SCN_EXPORT __declspec(dllexport)
#    else
        /* We are using this library */
#      define SCN_EXPORT __declspec(dllimport)
#    endif
#  endif

#  ifndef SCN_NO_EXPORT
#    define SCN_NO_EXPORT 
#  endif
#endif

#ifndef SCN_DEPRECATED
#  define SCN_DEPRECATED __declspec(deprecated)
#endif

#ifndef SCN_DEPRECATED_EXPORT
#  define SCN_DEPRECATED_EXPORT SCN_EXPORT SCN_DEPRECATED
#endif

#ifndef SCN_DEPRECATED_NO_EXPORT
#  define SCN_DEPRECATED_NO_EXPORT SCN_NO_EXPORT SCN_DEPRECATED
#endif

/* NOLINTNEXTLINE(readability-avoid-unconditional-preprocessor-if) */
#if 0 /* DEFINE_NO_DEPRECATED */
#  ifndef SCN_NO_DEPRECATED
#    define SCN_NO_DEPRECATED
#  endif
#endif

#endif /* SCN_EXPORT_H */
