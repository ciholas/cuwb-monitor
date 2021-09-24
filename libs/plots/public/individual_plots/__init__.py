# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import glob
import importlib
import inspect
from os.path import dirname, basename
import plots

# Local libraries
from utils import convert_to_snake_case

module_files = glob.glob(dirname(__file__)+"/*.py")
for module_file in module_files:
    if not module_file.endswith('__init__.py'):
        module_name = basename(module_file)[:-3]

        # Import the module
        module = importlib.import_module(__package__+'.'+module_name)

        for class_name, plot_obj in inspect.getmembers(module):
            if inspect.isclass(plot_obj) and module_name == convert_to_snake_case(class_name):
                plots.map_type_to_plot[plot_obj.type] = plot_obj

        # Emulate from X import *
        if "__all__" in module.__dict__:
            names = module.__dict__['__all__']
        else:
            names = [x for x in module.__dict__ if not x.startswith('_')]
        globals().update({k: getattr(module, k) for k in names})
