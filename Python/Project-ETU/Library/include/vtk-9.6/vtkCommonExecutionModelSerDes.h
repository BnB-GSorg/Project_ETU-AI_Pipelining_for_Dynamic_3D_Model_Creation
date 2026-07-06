// SPDX-FileCopyrightText: Copyright (c) Ken Martin, Will Schroeder, Bill Lorensen
// SPDX-License-Identifier: BSD-3-Clause
#ifndef vtkCommonExecutionModelSerDes_h
#define vtkCommonExecutionModelSerDes_h

#include "vtkCommonExecutionModelModule.h"

#define RegisterClasses_vtkCommonExecutionModel VTK_ABI_NAMESPACE_MANGLE(RegisterClasses_vtkCommonExecutionModel)

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
  VTKCOMMONEXECUTIONMODEL_EXPORT int RegisterClasses_vtkCommonExecutionModel(void* serializer, void* deserializer, void* invoker, const char** error);
}

VTK_ABI_NAMESPACE_END
#endif
// VTKHeaderTest-Exclude: vtkCommonExecutionModelSerDes.h
