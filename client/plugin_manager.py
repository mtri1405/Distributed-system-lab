import importlib

class PluginManager:
    def __init__(self):
        self.plugins = []

    def load_plugins(self, plugin_list):
        self.plugins = []
        for cls_path in plugin_list:
            try:
                module_name, class_name = cls_path.rsplit(".", 1)
                module = importlib.import_module(module_name)
                plugin_cls = getattr(module, class_name)
                instance = plugin_cls()
                instance.initialize({})
                self.plugins.append(instance)
            except Exception as e:
                print(f"Error loading {cls_path}: {e}")

    def get_plugins(self):
        return self.plugins