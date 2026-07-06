// SPDX-FileCopyrightText: Copyright (c) Ken Martin, Will Schroeder, Bill Lorensen
// SPDX-License-Identifier: BSD-3-Clause
#ifndef vtkInteractionWidgetsSerDes_h
#define vtkInteractionWidgetsSerDes_h

#include "vtkInteractionWidgetsModule.h"

#define RegisterClasses_vtkInteractionWidgets VTK_ABI_NAMESPACE_MANGLE(RegisterClasses_vtkInteractionWidgets)

VTK_ABI_NAMESPACE_BEGIN

extern "C"
{
  /**
   * Register the (de)serialization handlers of classes in a serialized library.
   * @param serializer   a vtkSerializer instance
   * @param deserializer a vtkDeserializer instance
   * @param invoker      a vtkInvoker instance
   * @param error        when registration fails, the error message is contained in `error`.
   * @warning The memory pointed to by `error` is NOT dynamically allocated. Do not free it.
   */
  VTKINTERACTIONWIDGETS_EXPORT int RegisterClasses_vtkInteractionWidgets(void* serializer, void* deserializer, void* invoker, const char** error);
}

VTK_ABI_NAMESPACE_END
#endif
// VTKHeaderTest-Exclude: vtkInteractionWidgetsSerDes.h
