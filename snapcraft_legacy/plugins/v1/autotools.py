# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2015-2016,2020 Canonical Ltd
# Copyright (C) 2016 Harald Sitter <sitter@kde.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""The autotools plugin is used for autotools based parts.

Autotools based projects are the ones that have the usual
`./configure && make && make install` instruction set.

The plugin tries to build using ./configure first, if it is not there
it will run ./autogen and if autogen is not there it will run autoreconf.

This plugin uses the common plugin keywords as well as those for "sources".
For more information check the 'plugins' topic for the former and the
'sources' topic for the latter.

In addition, this plugin uses the following plugin-specific keywords:

    - configflags:
      (list of strings)
      configure flags to pass to the build such as those shown by running
      './configure --help'
    - install-via:
      (enum, 'destdir' or 'prefix')
      Whether to install via DESTDIR or by using --prefix (default is
      'destdir')
"""

import os
from pathlib import Path

from snapcraft_legacy.plugins.v1 import make


class AutotoolsPlugin(make.MakePlugin):
    @classmethod
    def schema(cls):
        schema = super().schema()
        schema["properties"]["configflags"] = {
            "type": "array",
            "minitems": 1,
            "items": {"type": "string"},
            "default": [],
        }

        schema["properties"]["install-via"] = {
            "enum": ["destdir", "prefix"],
            "default": "destdir",
        }

        schema["required"] = ["source"]

        return schema

    @classmethod
    def get_build_properties(cls):
        # Inform Snapcraft of the properties associated with building. If these
        # change in the YAML Snapcraft will consider the build step dirty.
        return super().get_build_properties() + ["configflags", "install-via"]

    def __init__(self, name, options, project):
        super().__init__(name, options, project)
        self.build_packages.extend(["autoconf", "automake", "autopoint", "libtool"])

        if options.install_via == "destdir":
            self.options.make_install_var = "DESTDIR"
        elif options.install_via == "prefix":
            self.options.make_install_var = ""
        else:
            raise RuntimeError(
                'Unsupported installation method: "{}"'.format(options.install_via)
            )

    def enable_cross_compilation(self):
        pass

    def build(self):
        configure_script = Path(self.builddir) / "configure"
        if not configure_script.exists():
            potential_scripts = [
                Path(self.builddir) / s for s in ["autogen.sh", "bootstrap"]
            ]
            existing_scripts = [
                s for s in potential_scripts if s.exists() and s.is_file()
            ]

            # If there are not alternative configure scripts, run autoreconf.
            if not existing_scripts:
                self.run(["autoreconf", "-i"])
            else:
                # Pick the first one.
                script = existing_scripts[0]
                # Make sure it's executable.
                if not os.access(script, os.X_OK):
                    script.chmod(0o755)
                self.run(["env", "NOCONFIGURE=1", script])

        configure_command = ["./configure"]

        if self.options.make_install_var:
            # Use an empty prefix since we'll install via DESTDIR
            configure_command.append("--prefix=")
        else:
            configure_command.append("--prefix=" + self.installdir)
        if self.project.is_cross_compiling:
            configure_command.append("--host={}".format(self.project.arch_triplet))

        self.run(configure_command + self.options.configflags)
        self.make()

    def snap_fileset(self):
        fileset = super().snap_fileset()
        # Remove .la files which don't work when they are moved around
        fileset.append("-**/*.la")
        return fileset
