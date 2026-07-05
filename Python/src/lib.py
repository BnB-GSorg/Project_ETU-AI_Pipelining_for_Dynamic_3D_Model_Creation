import os, sys
import math
import tqdm

# Detect OS and add OS-specific modules
def install_from_OS(version_specific: bool = False):
    '''install from OS
    
    args:
        - version_specific (boolean): if True, check on the OS version too
        
    install OS-specific modules
    
    output:
        - None
    
    '''
    
    import platform
    
    installation_process = tqdm.tqdm(total = 2)
    print("Installing modules ...")
    
    if not version_specific: 
        match sys.platform:
            case 'win32':
                import libUNIX
            case 'linux' | 'linux2' | 'darwin':
                import libLINIX
            case _: import libUNIX
        installation_process.update(1)
    else: 
        os_name = platform.system()
        os_version = platform.version()
        if os_name == 'Windows':
            pass
        if os_name == 'Linux':
            pass
        if os_name == 'Darwin':
            pass
        install_from_OS(version_specific = False)
        installation_process.update(1)
    installation_process.update(1)
    
    installation_process.close()
    
    
