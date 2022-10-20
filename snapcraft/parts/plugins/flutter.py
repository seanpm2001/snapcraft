from typing import List, Dict, Set, cast, Literal, Any

from craft_parts import plugins

FLUTTER_REPO = "https://github.com/flutter/flutter.git "

class FlutterPluginProperties(plugins.PluginProperties, plugins.PluginModel):
    flutter_branch: Literal["stable", "master", "dev"] = "stable"
    flutter_target: str = "lib/main.dart"

    @classmethod
    def unmarshal(cls, data: Dict[str, Any]) -> "CondaPluginProperties":
        """Populate class attributes from the part specification.

        :param data: A dictionary containing part properties.

        :return: The populated plugin properties data object.

        :raise pydantic.ValidationError: If validation fails.
        """
        plugin_data = plugins.extract_plugin_properties(
            data,
            plugin_name="flutter",
        )
        return cls(**plugin_data)


class FlutterPlugin(plugins.Plugin):

    properties_class = FlutterPluginProperties

    def get_build_snaps(self) -> Set[str]:
        return {}

    def get_build_packages(self) -> Set[str]:
        return {
            "clang",
            "git",
            "cmake",
            "ninja-build",
            "unzip",
        }

    def get_build_environment(self) -> Dict[str, str]:
        return {
            "PATH": "$CRAFT_PART_BUILD/flutter-distro/bin:$PATH",
        }

    def _get_setup_flutter(self, options):
        return [
            f"[ -d flutter-distro ] || git clone -b {options.flutter_branch} {FLUTTER_REPO} flutter-distro",
            "flutter doctor",
            "flutter pub get",
        ]

    def get_build_commands(self) -> List[str]:
        options = cast(FlutterPluginProperties, self._options)
        flutter_install_cmd = self._get_setup_flutter(options)
        flutter_build_cmd = [
            f"flutter build linux --release -v -t {options.flutter_target}",
            "mkdir -p $CRAFT_PART_INSTALL/bin/",
            "cp -r build/linux/*/release/bundle/* $CRAFT_PART_INSTALL/bin/",
        ]
        return flutter_install_cmd + flutter_build_cmd
