/*****************************************************************************/
/*                                    XDMF                                   */
/*                       eXtensible Data Model and Format                    */
/*                                                                           */
/*  Id : XdmfCoreConfig.hpp                                                  */
/*                                                                           */
/*  Author:                                                                  */
/*     Kenneth Leiter                                                        */
/*     kenneth.leiter@arl.army.mil                                           */
/*     US Army Research Laboratory                                           */
/*     Aberdeen Proving Ground, MD                                           */
/*                                                                           */
/*     Copyright @ 2011 US Army Research Laboratory                          */
/*     All Rights Reserved                                                   */
/*     See Copyright.txt for details                                         */
/*                                                                           */
/*     This software is distributed WITHOUT ANY WARRANTY; without            */
/*     even the implied warranty of MERCHANTABILITY or FITNESS               */
/*     FOR A PARTICULAR PURPOSE.  See the above copyright notice             */
/*     for more information.                                                 */
/*                                                                           */
/*****************************************************************************/

#ifndef XDMFCORECONFIG_HPP_
#define XDMFCORECONFIG_HPP_

/* #undef HAVE_BOOST_SHARED_DYNAMIC_CAST */
/* #undef XDMF_BIG_ENDIAN */

#define BUILD_SHARED
#ifndef BUILD_SHARED
#  define XDMFSTATIC
#endif

#define XDMF_NO_REALPATH

#endif /* XDMFCORECONFIG_HPP_ */
