# -*- Mode:Python; indent-tabs-mode:nil; tab-width:4 -*-
#
# Copyright (C) 2015-2018 Canonical Ltd
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

import os
from unittest.mock import MagicMock, patch

import pytest
from snaphelpers import SnapCtlError
from testtools.matchers import Equals

from snapcraft_legacy.internal import common, errors
from tests.legacy import unit


@pytest.fixture
def mock_config():
    with patch(
        "snapcraft_legacy.internal.common.SnapConfigOptions", autospec=True
    ) as mock_snap_config:
        yield mock_snap_config


@pytest.fixture()
def mock_is_snap(mocker):
    yield mocker.patch("snapcraft_legacy.internal.common.is_snap", return_value=True)


class CommonTestCase(unit.TestCase):
    def test_set_plugindir(self):
        plugindir = os.path.join(self.path, "testplugin")
        common.set_plugindir(plugindir)
        self.assertThat(plugindir, Equals(common.get_plugindir()))


def test_isurl():
    assert common.isurl("git://") is True
    assert common.isurl("bzr://") is True
    assert common.isurl("./") is False
    assert common.isurl("/foo") is False
    assert common.isurl("/foo:o") is False


class CommonMigratedTestCase(unit.TestCase):
    def test_parallel_build_count_migration_message(self):
        raised = self.assertRaises(
            errors.PluginOutdatedError, common.get_parallel_build_count
        )

        self.assertThat(
            str(raised), Equals("This plugin is outdated: use 'parallel_build_count'")
        )

    def test_deb_arch_migration_message(self):
        raised = self.assertRaises(errors.PluginOutdatedError, common.get_arch)

        self.assertThat(
            str(raised), Equals("This plugin is outdated: use 'project.deb_arch'")
        )

    def test_arch_triplet_migration_message(self):
        raised = self.assertRaises(errors.PluginOutdatedError, common.get_arch_triplet)

        self.assertThat(
            str(raised), Equals("This plugin is outdated: use 'project.arch_triplet'")
        )


class FormatInColumnsTestCase(unit.TestCase):

    elements_list = [
        "ant",
        "autotools",
        "catkin",
        "cmake",
        "copy",
        "go",
        "jdk",
        "kbuild",
        "kernel",
        "make",
        "maven",
        "nil",
        "nodejs",
        "python2",
        "python3",
        "scons",
        "tar-content",
    ]

    def test_format_output_in_columns_default(self):
        """Format output on 2 lines, with default max-width and space sep"""
        expected = [
            "ant        catkin  copy  jdk     kernel  maven  "
            "nodejs   python3  tar-content",
            "autotools  cmake   go    kbuild  make    nil    python2  scons  ",
        ]
        self.assertThat(
            common.format_output_in_columns(self.elements_list), Equals(expected)
        )

    def test_format_output_in_columns_narrow(self):
        """Format output on 3 lines, with narrow max-width and space sep"""
        expected = [
            "ant        cmake  jdk     make   nodejs   scons      ",
            "autotools  copy   kbuild  maven  python2  tar-content",
            "catkin     go     kernel  nil    python3",
        ]
        self.assertThat(
            common.format_output_in_columns(self.elements_list, max_width=60),
            Equals(expected),
        )

    def test_format_output_in_columns_large(self):
        """Format output on one big line, with default space sep"""
        expected = [
            "ant  autotools  catkin  cmake  copy  go  jdk  kbuild  "
            "kernel  make  maven  nil  nodejs  python2  python3  "
            "scons  tar-content"
        ]
        self.assertThat(
            common.format_output_in_columns(self.elements_list, max_width=990),
            Equals(expected),
        )

    def test_format_output_in_columns_one_space(self):
        """Format output with one space sep"""
        expected = [
            "ant       cmake jdk    make  nodejs  scons      ",
            "autotools copy  kbuild maven python2 tar-content",
            "catkin    go    kernel nil   python3",
        ]
        self.assertThat(
            common.format_output_in_columns(
                self.elements_list, max_width=60, num_col_spaces=1
            ),
            Equals(expected),
        )


class TestFormatSnapFileName:

    scenarios = [
        (
            "all info",
            dict(
                snap=dict(name="name", version="version", architectures=["amd64"]),
                expected="name_version_amd64.snap",
            ),
        ),
        (
            "missing version",
            dict(
                snap=dict(name="name", architectures=["amd64"]),
                expected="name_amd64.snap",
            ),
        ),
        (
            "no arch",
            dict(
                snap=dict(name="name", version="version"),
                expected="name_version_all.snap",
            ),
        ),
        (
            "multi",
            dict(
                snap=dict(
                    name="name", version="version", architectures=["amd64", "i386"]
                ),
                expected="name_version_multi.snap",
            ),
        ),
        (
            "pack",
            dict(
                snap=dict(name="name", version="version", arch=["amd64"]),
                expected="name_version_amd64.snap",
            ),
        ),
        (
            "pack multi",
            dict(
                snap=dict(name="name", version="version", arch=["amd64", "i386"]),
                expected="name_version_multi.snap",
            ),
        ),
    ]

    def test_filename(self, snap, expected):
        if "version" not in snap:
            snap_name = common.format_snap_name(snap, allow_empty_version=True)
        else:
            snap_name = common.format_snap_name(snap)

        assert snap_name == expected


def test_version_missing_and_not_allowed_is_error():
    # This is to not experience unexpected results given the
    # fact that version is not allowed.
    with pytest.raises(KeyError):
        common.format_snap_name(dict(name="name"))


@pytest.mark.parametrize("provider", ["lxd", "multipass"])
def test_get_snap_config(mock_config, mock_is_snap, provider):
    """Verify getting a valid snap config."""

    def fake_as_dict():
        return {"provider": provider}

    mock_config.return_value.as_dict.side_effect = fake_as_dict

    assert common.get_snap_config() == {"provider": provider}


def test_get_snap_config_empty(mock_config, mock_is_snap):
    """Verify getting an empty config returns a default SnapConfig."""

    def fake_as_dict():
        return {}

    mock_config.return_value.as_dict.side_effect = fake_as_dict

    assert common.get_snap_config() == {}


def test_get_snap_config_not_from_snap(mock_is_snap, mocker):
    """Verify None is returned when snapcraft is not running from a snap."""
    mock_is_snap.return_value = False

    assert common.get_snap_config() is None


@pytest.mark.parametrize("error", [AttributeError, SnapCtlError(process=MagicMock())])
def test_get_snap_config_handle_init_error(error, mock_config, mock_is_snap):
    """An error when initializing the snap config object should return None."""
    mock_config.side_effect = error

    assert common.get_snap_config() is None


@pytest.mark.parametrize("error", [AttributeError, SnapCtlError(process=MagicMock())])
def test_get_snap_config_handle_fetch_error(error, mock_config, mock_is_snap):
    """An error when fetching the snap config should return None."""
    mock_config.return_value.fetch.side_effect = error

    assert common.get_snap_config() is None
