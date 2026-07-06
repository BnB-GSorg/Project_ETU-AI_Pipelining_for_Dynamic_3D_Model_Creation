// SPDX-FileCopyrightText: Copyright (c) Ken Martin, Will Schroeder, Bill Lorensen
// SPDX-License-Identifier: BSD-3-Clause
#ifndef vtkRenderingLICOpenGL2SerDes_h
#define vtkRenderingLICOpenGL2SerDes_h

#include "vtkRenderingLICOpenGL2Module.h"

#define RegisterClasses_vtkRenderingLICOpenGL2 VTK_ABI_NAMESPACE_MANGLE(RegisterClasses_vtkRenderingLICOpenGL2)

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
  VTKRENDERINGLICOPENGL2_EXPORT int RegisterClasses_vtkRenderingLICOpenGL2(void* serializer, void* deserializer, void* invoker, const char** error);
}

VTK_ABI_NAMESPACE_END
#endif
// VTKHeaderTest-Exclude: vtkRenderingLICOpenGL2SerDes.h
