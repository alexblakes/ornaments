"""Build the bundled engine with tools already installed in the environment."""
from pathlib import Path
import subprocess

from setuptools import Distribution, setup
from setuptools.command.build_py import build_py


class NativeDistribution(Distribution):
    def has_ext_modules(self):
        # The bundled executable needs a platform wheel and a platlib install.
        return True


class BuildPy(build_py):
    def run(self):
        super().run()
        source = Path(__file__).resolve().parent
        build = self.get_finalized_command("build")
        native_build = Path(build.build_temp).resolve() / "native"
        subprocess.run([
            "cmake", "-S", str(source), "-B", str(native_build),
            "-DCMAKE_BUILD_TYPE=Release", "-DUSE_HDF5=OFF",
            "-DORNAMENTS_INSTALL_DIR=ornaments/_bin",
        ], check=True)
        subprocess.run(["cmake", "--build", str(native_build)], check=True)
        subprocess.run([
            "cmake", "--install", str(native_build),
            "--prefix", str(Path(self.build_lib).resolve()),
        ], check=True)

    def get_outputs(self, include_bytecode=1):
        return super().get_outputs(include_bytecode) + [
            str(Path(self.build_lib) / "ornaments" / "_bin" / "ornaments")
        ]


setup(distclass=NativeDistribution, cmdclass={"build_py": BuildPy})
