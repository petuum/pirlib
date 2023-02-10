# Copyright 2022 Petuum, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os

import setuptools

if __name__ == "__main__":
    setuptools.setup(
        name="pirlib",
        version=os.getenv("PIRLIB_VERSION", "0.0.0"),
        author="Petuum Inc.",
        author_email="aurick.qiao@petuum.com",
        description="Python library for unified ML pipelines",
        url="https://github.com/petuum/pirlib",
        classifiers=[
            "Programming Language :: Python :: 3",
            "License :: Other/Proprietary License",
            "Operating System :: POSIX :: Linux",
        ],
        packages=setuptools.find_packages(include=["pirlib", "pirlib.*"]),
        python_requires=">=3.8",
        install_requires=["dacite>=1.6", "pyyaml>=6.0", "typeguard>=2.13", "diskcache==5.4.0"],
    )
