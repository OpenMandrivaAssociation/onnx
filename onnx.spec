%define _disable_ld_no_undefined 1
%global _empty_manifest_terminate_build 0

%define libname %mklibname onnx
%define devname %mklibname -d onnx

Name:       onnx
# This is intentionally an old version.
# Please don't update it until this issue is fixed
# or someone has ported the patch
# https://github.com/microsoft/onnxruntime/issues/24561
Version:    1.22.0
Release:    4
Summary:    Open standard for machine learning interoperability
License:    Apache-2.0
Group:      Development/Python

URL:        https://github.com/onnx/onnx
Source0:    https://github.com/onnx/onnx/archive/v%{version}/%{name}-%{version}.tar.gz

BuildRequires:  cmake >= 3.13
BuildRequires:  ninja
BuildRequires:  make
BuildRequires:  findutils
BuildRequires:  zlib-devel
BuildRequires:  pkgconfig(python3)
BuildRequires:  python%{pyver}dist(pip)
BuildRequires:  python%{pyver}dist(protobuf)
BuildRequires:  python%{pyver}dist(pytest)
BuildRequires:  python%{pyver}dist(pybind11)
BuildRequires:  python%{pyver}dist(setuptools)
BuildRequires:  python%{pyver}dist(scikit-build-core)
BuildRequires:  python%{pyver}dist(numpy)
BuildRequires:  python%{pyver}dist(ml-dtypes)
BuildRequires:  python%{pyver}dist(typing-extensions)
BuildRequires:  python%{pyver}dist(nanobind)
BuildRequires:  cmake(pybind11)
BuildRequires:  protobuf-devel

%patchlist
# Build shared libraries and fix install location 
# dropped (no longer applies): https://src.fedoraproject.org/rpms/onnx/raw/rawhide/f/0000-Build-shared-libraries-and-fix-install-location.patch
# Use system protobuf and require parameterized
# dropped (no longer applies): https://src.fedoraproject.org/rpms/onnx/raw/rawhide/f/0002-Use-system-protobuf-and-require-parameterized.patch
# Add fixes for use with onnxruntime
# dropped (no longer applies): https://src.fedoraproject.org/rpms/onnx/raw/rawhide/f/0004-Add-fixes-for-use-with-onnxruntime.patch
# dropped (no longer applies): onnx-allow-current-protobuf.patch
# Fix linkage
#onnx-absl-linkage.patch

%global _description %{expand:
%{name} provides an open source format for AI models, both deep learning and
traditional ML. It defines an extensible computation graph model, as well as
definitions of built-in operators and standard data types.}

%description %_description

%package -n %{libname}
Summary:    Libraries for %{name}

%description -n %{libname} %_description

%package -n %{devname}
Summary:    Development files for %{name}
Requires:   %{libname} = %{EVRD}

%description -n %{devname} %_description

%package -n python-onnx
Summary:    %{summary}
Requires:   %{libname} = %{EVRD}

%description -n python-onnx %_description

%prep
%autosetup -p1 -n onnx-%{version}
# Drop nbval options from pytest. Plugin is not available in Fedora.
# 1.22 pins the build backend to protobuf 4.25.1 and tags the wheel cp312.
# Cooker protobuf is 6.x and the interpreter is 3.15.
sed -r \
    -e 's/--nbval //' \
    -e 's/--nbval-current-env //' \
    -e 's/protobuf==4.25.1/protobuf>=4.25.1/' \
    -e '/wheel.py-api/d' \
    -i pyproject.toml

# Make absl Great Again
sed -i -e 's,CMAKE_CXX_STANDARD 17,CMAKE_CXX_STANDARD 20,g' CMakeLists.txt
# 1.22 installs libonnx.so with no soname. Keep the versioned runtime library.
sed -i '/CXX_VISIBILITY_PRESET hidden/a set_target_properties(onnx onnx_proto PROPERTIES VERSION ${ONNX_VERSION} SOVERSION ${ONNX_VERSION})' CMakeLists.txt

%build
# ORT links symbols that are not marked ONNX_API: OpSchema::Attr templates,
# DataTypeUtils::ToType, ParseData, ReplaceAll, loaded_schema_version.
# Hidden visibility leaves them out of libonnx.so. The Python extension
# must stay hidden, or both DSOs export the type-map singleton.
# ninja install re-runs CMake when CMakeLists.txt is newer. 1.22.0-3
# restored hidden visibility for the Python build, and that reconfigure
# relinked the hidden library. Save the default-visibility libraries
# and copy them back over that relink.
sed -i 's/CXX_VISIBILITY_PRESET hidden/CXX_VISIBILITY_PRESET default/' CMakeLists.txt
export CMAKE_BUILD_DIR=cxxbuild
%cmake \
    -DONNX_USE_LITE_PROTO=OFF \
    -DONNX_USE_PROTOBUF_SHARED_LIBS=ON \
    -DCMAKE_SKIP_RPATH:BOOL=ON \
    -DBUILD_ONNX_PYTHON:BOOL=ON \
    -DPY_SITEARCH=%{python3_sitearch} \
    -G Ninja
%ninja_build
mkdir -p %{_builddir}/onnx-shared
cp -a libonnx.so* libonnx_proto.so* %{_builddir}/onnx-shared/

cd ..
unset CMAKE_BUILD_DIR
sed -i 's/CXX_VISIBILITY_PRESET default/CXX_VISIBILITY_PRESET hidden/' CMakeLists.txt
# Build python libs. Release wheels have no DWARF and fail the build.
# 1.22 runs "python -m nanobind" and otherwise git-clones nanobind.
export SKBUILD_CMAKE_BUILD_TYPE=RelWithDebInfo
export CMAKE_ARGS="-DFETCHCONTENT_FULLY_DISCONNECTED=ON"
%py_build

%install
%ninja_install -C cxxbuild
cp -a %{_builddir}/onnx-shared/libonnx.so* %{_builddir}/onnx-shared/libonnx_proto.so* %{buildroot}%{_libdir}/
# Fail here if the installed library is still the hidden one.
nm -D --defined-only %{buildroot}%{_libdir}/libonnx.so.%{version} | grep -q 13DataTypeUtils || {
    echo "libonnx.so is missing DataTypeUtils exports" >&2
    exit 1
}
# The Python build drops CMakeFiles into directories that the C++ install copies.
find "%{buildroot}%{_includedir}" -depth -type d -name CMakeFiles -print0 | xargs -0 -r rm -rf
find "%{buildroot}%{_includedir}" -type d -empty -delete
# Install *.proto files
install -p "./onnx/"*.proto -t "%{buildroot}%{_includedir}/onnx/"

%py_install
# The Python tree does not exist until the wheel is installed.
if [ -d "%{buildroot}%{python3_sitearch}" ]; then
	find "%{buildroot}%{python3_sitearch}" -type d -empty -delete
fi

%files -n %{libname}
%license LICENSE
%doc README.md
%{_libdir}/libonnx.so.%{version}
%{_libdir}/libonnx_proto.so.%{version}

%files -n %{devname}
%{_libdir}/libonnx.so
%{_libdir}/libonnx_proto.so
%{_libdir}/cmake/ONNX
%{_includedir}/%{name}/

%files -n python-onnx
%{_bindir}/backend-test-tools
%{_bindir}/check-model
%{_bindir}/check-node
%{python3_sitearch}/onnx
%{python3_sitearch}/onnx-%{version}*.dist-info
