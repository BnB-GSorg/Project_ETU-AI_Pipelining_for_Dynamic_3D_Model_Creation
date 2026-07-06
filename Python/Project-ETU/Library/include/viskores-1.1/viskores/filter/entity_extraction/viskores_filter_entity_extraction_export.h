//============================================================================
//  The contents of this file are covered by the Viskores license. See
//  LICENSE.txt for details.
//
//  By contributing to this file, all contributors agree to the Developer
//  Certificate of Origin Version 1.1 (DCO 1.1) as stated in DCO.txt.
//============================================================================

//============================================================================
//  Copyright (c) Kitware, Inc.
//  All rights reserved.
//  See LICENSE.txt for details.
//
//  This software is distributed WITHOUT ANY WARRANTY; without even
//  the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
//  PURPOSE.  See the above copyright notice for more information.
//============================================================================
#ifndef VISKORES_FILTER_ENTITY_EXTRACTION_EXPORT_H
#define VISKORES_FILTER_ENTITY_EXTRACTION_EXPORT_H

#if defined(VISKORES_DOXYGEN_ONLY)
#   define VISKORES_FILTER_ENTITY_EXTRACTION_EXPORT_DEFINE
#   define VISKORES_FILTER_ENTITY_EXTRACTION_IMPORT_DEFINE
#   define VISKORES_FILTER_ENTITY_EXTRACTION_NO_EXPORT_DEFINE
#elif defined(_MSC_VER)
# if 0
    /* This is a static component and has no need for exports
       elf based static libraries are able to have hidden/default visibility
       controls on symbols so we should propagate this information in that
       use case
    */
#   define VISKORES_FILTER_ENTITY_EXTRACTION_EXPORT_DEFINE
#   define VISKORES_FILTER_ENTITY_EXTRACTION_IMPORT_DEFINE
#   define VISKORES_FILTER_ENTITY_EXTRACTION_NO_EXPORT_DEFINE
# else
#   define VISKORES_FILTER_ENTITY_EXTRACTION_EXPORT_DEFINE __declspec(dllexport)
#   define VISKORES_FILTER_ENTITY_EXTRACTION_IMPORT_DEFINE __declspec(dllimport)
#   define VISKORES_FILTER_ENTITY_EXTRACTION_NO_EXPORT_DEFINE
# endif
#else
#   define VISKORES_FILTER_ENTITY_EXTRACTION_EXPORT_DEFINE __attribute__((visibility("default")))
#   define VISKORES_FILTER_ENTITY_EXTRACTION_IMPORT_DEFINE __attribute__((visibility("default")))
#   define VISKORES_FILTER_ENTITY_EXTRACTION_NO_EXPORT_DEFINE __attribute__((visibility("hidden")))
#endif

#ifndef VISKORES_FILTER_ENTITY_EXTRACTION_EXPORT
# if defined(viskores_filter_entity_extraction_EXPORTS)
    /* We are building this library */
#   define VISKORES_FILTER_ENTITY_EXTRACTION_EXPORT VISKORES_FILTER_ENTITY_EXTRACTION_EXPORT_DEFINE
# else
    /* We are using this library */
#   define VISKORES_FILTER_ENTITY_EXTRACTION_EXPORT VISKORES_FILTER_ENTITY_EXTRACTION_IMPORT_DEFINE
# endif
#endif

#ifndef VISKORES_FILTER_ENTITY_EXTRACTION_TEMPLATE_EXPORT
# if defined(viskores_filter_entity_extraction_EXPORTS) && defined(_MSC_VER)
  /* Warning C4910 on windows state that extern explicit template can't be
     labeled with __declspec(dllexport). So that is why we use a new custom
     define. But when other modules ( e.g. rendering ) include this header
     we need them to see that the extern template is actually being imported.
  */
    /* We are building this library with MSVC */
#   define VISKORES_FILTER_ENTITY_EXTRACTION_TEMPLATE_EXPORT
# elif defined(viskores_filter_entity_extraction_EXPORTS)
    /* We are building this library */
#   define VISKORES_FILTER_ENTITY_EXTRACTION_TEMPLATE_EXPORT VISKORES_FILTER_ENTITY_EXTRACTION_EXPORT_DEFINE
# else
    /* We are using this library */
#   define VISKORES_FILTER_ENTITY_EXTRACTION_TEMPLATE_EXPORT VISKORES_FILTER_ENTITY_EXTRACTION_IMPORT_DEFINE
# endif
#endif

#ifndef VISKORES_FILTER_ENTITY_EXTRACTION_NO_EXPORT
  #define VISKORES_FILTER_ENTITY_EXTRACTION_NO_EXPORT VISKORES_FILTER_ENTITY_EXTRACTION_NO_EXPORT_DEFINE
#endif

#endif
