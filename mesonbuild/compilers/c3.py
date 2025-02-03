# SPDX-License-Identifier: Apache-2.0
# Copyright 2025 Karurochari
# Based on the swift backend for now since it is the most similar.

from __future__ import annotations

import re
import subprocess, os.path
import typing as T

from .. import mlog
from ..mesonlib import EnvironmentException, MesonException
from .compilers import Compiler, clike_debug_args


if T.TYPE_CHECKING:
    from ..dependencies import Dependency
    from ..envconfig import MachineInfo
    from ..environment import Environment
    from ..linkers.linkers import DynamicLinker
    from ..mesonlib import MachineChoice

c3_optimization_args: T.Dict[str, T.List[str]] = {
    'plain': [],
    '0': ['-O0'],
    'g': ['-Og'],
    '1': ['-O1'],
    '2': ['-O2'],
    '3': ['-O3'],
    's': ['-Os'],
    '4': ['-O4'],
    '5': ['-O5'],
    'z': ['-Oz'],
}

class C3Compiler(Compiler):

    LINKER_PREFIX = ['compile','--linker=builtin','--no-entry','-z']    # Temporary fix for now. The linker should not require builtin to work but well...
    language = 'c3'
    id = 'llvm'

    def __init__(self, exelist: T.List[str], version: str, for_machine: MachineChoice,
                 is_cross: bool, info: 'MachineInfo', full_version: T.Optional[str] = None,
                 linker: T.Optional['DynamicLinker'] = None):
        super().__init__([], exelist, version, for_machine, info,
                         is_cross=is_cross, full_version=full_version,
                         linker=linker)
        self.version = version
        if self.info.is_darwin():
            try:
                self.sdk_path = subprocess.check_output(['xcrun', '--show-sdk-path'],
                                                        universal_newlines=True,
                                                        encoding='utf-8', stderr=subprocess.STDOUT).strip()
            except subprocess.CalledProcessError as e:
                mlog.error("Failed to get Xcode SDK path: " + e.output)
                raise MesonException('Xcode license not accepted yet. Run `sudo xcodebuild -license`.')
            except FileNotFoundError:
                mlog.error('xcrun not found. Install Xcode to compile Swift code.')
                raise MesonException('Could not detect Xcode. Please install it to compile Swift code.')

    def get_pic_args(self) -> T.List[str]:
        return []

    def get_pie_args(self) -> T.List[str]:
        return []

    def needs_static_linker(self) -> bool:
        return True

    def get_werror_args(self) -> T.List[str]:
        return []

    def get_dependency_gen_args(self, outtarget: str, outfile: str) -> T.List[str]:
        return []   #TODO:c3c I need to check if there is something like that supported in here

    def get_dependency_compile_args(self, dep: Dependency) -> T.List[str]:
        return []

    def depfile_for_object(self, objfile: str) -> T.Optional[str]:
        #return os.path.splitext(objfile)[0] + '.' + self.get_depfile_suffix()
        return None

    def get_depfile_suffix(self) -> str:
        return 'd'

    def get_output_args(self, target: str) -> T.List[str]:
        return ['-o', target]

    def get_warn_args(self, level: str) -> T.List[str]:
        return []

    def get_std_exe_link_args(self) -> T.List[str]:
        return []

    def get_include_args(self, path: str, is_system: bool) -> T.List[str]:
        return ['--libdir' , path]

    def get_compile_only_args(self) -> T.List[str]:
        return ['compile-only']

    def compute_parameters_with_absolute_paths(self, parameter_list: T.List[str],
                                               build_dir: str) -> T.List[str]:
        for idx, i in enumerate(parameter_list):
            if i[:2] == '-I' or i[:2] == '-L':
                parameter_list[idx] = i[:2] + os.path.normpath(os.path.join(build_dir, i[2:]))

        return parameter_list

    def sanity_check(self, work_dir: str, environment: 'Environment') -> None:
        src = 'c3ctest.c3'
        source_name = os.path.join(work_dir, src)
        output_name = os.path.join(work_dir, 'c3test', 'c3test')
        extra_flags: T.List[str] = []
        extra_flags += environment.coredata.get_external_args(self.for_machine, self.language)
        if self.is_cross:
            extra_flags += self.get_compile_only_args()
        else:
            extra_flags += environment.coredata.get_external_link_args(self.for_machine, self.language)
        with open(source_name, 'w', encoding='utf-8') as ofile:
            ofile.write('''fn int main(){return 0;}
''')
        pc = subprocess.Popen(self.exelist + extra_flags + ['compile', src, '-o', output_name], cwd=work_dir)
        pc.wait()
        if pc.returncode != 0:
            raise EnvironmentException('C3 compiler %s cannot compile programs.' % self.name_string())
        if self.is_cross:
            # Can't check if the binaries run so we have to assume they do
            return
        if subprocess.call(output_name) != 0:
            raise EnvironmentException('Executables created by C3 compiler %s are not runnable.' % self.name_string())

    def get_debug_args(self, is_debug: bool) -> T.List[str]:
        return clike_debug_args[is_debug]

    def get_optimization_args(self, optimization_level: str) -> T.List[str]:
        return c3_optimization_args[optimization_level]
