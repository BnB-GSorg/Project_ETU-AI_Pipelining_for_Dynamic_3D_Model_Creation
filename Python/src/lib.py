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
    

class after_installation_checkings:
    
    def __init__(self):
        self.stdlib_providers = {
            'gzip':            'compression_lib.py',
            'tarfile':         'compression_lib.py',
            'zipfile':         'compression_lib.py',
            'configparser':    'config_formats_lib.py',
            'plistlib':        'config_formats_lib.py',
            'tomllib':         'config_formats_lib.py',
            'hashlib':         'crypto_lib.py',
            'hmac':            'crypto_lib.py',
            'sqlite3':         'data_persistence_lib.py',
            'collections':     'data_types_lib.py',
            'collections.abc': 'data_types_lib.py',
            'copy':            'data_types_lib.py',
            'enum':            'data_types_lib.py',
            'queue':           'data_types_lib.py',
            'types':           'data_types_lib.py',
            'filecmp':         'file_access_lib.py',
            'fileinput':       'file_access_lib.py',
            'pathlib':         'file_access_lib.py',
            'os.path':         'file_access_lib.py',
            'itertools':       'functional_lib.py',
            'operator':        'functional_lib.py',
            'tkinter':         'gui_lib.py',
            'idlelib':         'gui_lib.py',
            'email':           'internet_lib.py',
            'json':            'internet_lib.py',
            'html':            'internet_lib.py',
            'urllib':          'internet_lib.py',
            'webbrowser':      'internet_lib.py',
            'abc':             'language_services_lib.py',
            'ast':             'language_services_lib.py',
            'gc':              'language_services_lib.py',
            'site':            'language_services_lib.py',
            'importlib':       'language_services_lib.py',
            'runpy':           'language_services_lib.py',
            'pkgutil':         'language_services_lib.py',
            'zipimport':       'language_services_lib.py',
            'tabnanny':        'language_services_lib.py',
            'audioop':         'multimedia_lib.py',
            'wave':            'multimedia_lib.py',
            'colorsys':        'multimedia_lib.py',
            'cmath':           'numeric_lib.py',
            'math':            'numeric_lib.py',
            'numbers':         'numeric_lib.py',
            'argparse':        'os_services_lib.py',
            'atexit':          'os_services_lib.py',
            'errno':           'os_services_lib.py',
            'gettext':         'os_services_lib.py',
            'mmap':            'os_services_lib.py',
            'platform':        'os_services_lib.py',
            'multiprocessing': 'os_services_lib.py',
            'threading':       'os_services_lib.py',
            'warnings':        'os_services_lib.py',
            'packaging':       'packaging_lib.py',
            'cmd':             'program_frameworks_lib.py',
            'string':          'text_processing_lib.py',
            'difflib':         'text_processing_lib.py',
        }
        self.external_dependencies = ['numpy', 'pandas', 'matplotlib', 'scipy', 'sklearn']
        import main
        self.default_installation_path = main.default_installation_path
    
    def _find_stdlib_provider(self, package_name):
        return self.stdlib_providers.get(package_name, None)
    
    def _install_external_package(self, package):
        import subprocess
        import venv
        from pathlib import Path
        
        venv_path = os.path.abspath(self.default_installation_path)
        if not os.path.exists(venv_path):
            print(f"Creating virtual environment at {venv_path} ...")
            venv.create(venv_path, with_pip=True)
        
        for candidate in Path(venv_path).rglob('python*'):
            if candidate.is_file() and candidate.name in ('python', 'python3', 'python.exe', 'python3.exe'):
                python_exe = str(candidate)
                break
        else:
            raise RuntimeError(f"Could not locate Python interpreter in {venv_path}")
        
        print(f"Installing {package} into virtual environment ...")
        subprocess.check_call([python_exe, '-m', 'pip', 'install', package])
        print(f"{package} installed successfully.")
    
    def check_dependencies(self):
        
        import importlib.util
        
        for dependency in self.external_dependencies:
            if importlib.util.find_spec(dependency) is not None:
                print(f"{dependency} is already installed.")
            else:
                if dependency in self.stdlib_providers:
                    provider = self.stdlib_providers[dependency]
                    print(f"{dependency} is a stdlib module provided by '{provider}'. No installation needed.")
                else:
                    print(f"{dependency} is not installed.")
                    self._install_external_package(dependency)
