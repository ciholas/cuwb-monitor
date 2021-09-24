# Ciholas, Inc. - www.ciholas.com
# Licensed under: creativecommons.org/licenses/by/4.0

# System libraries
import glob
import importlib
from os.path import dirname, basename

map_type_to_plot = dict()
map_type_to_aggregate_plot = dict()

module_files = glob.glob(dirname(__file__)+"/*/*")
for module_file in module_files:
    if module_file.endswith('_plots'):
        module_name = basename(dirname(module_file)) + "." + basename(module_file)

        # Import the module
        module = importlib.import_module(__package__+'.'+module_name)

        if "__all__" in module.__dict__:
            names = module.__dict__['__all__']
        else:
            names = [x for x in module.__dict__ if not x.startswith('_')]
        globals().update({k: getattr(module, k) for k in names})
