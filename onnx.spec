%define _disable_ld_no_undefined 1

%define libname %mklibname onnx
%define devname %mklibname -d onnx

Name:       onnx
Version:    1.18.0
Release:    1
Summary:    Open standard for machine learning interoperability
License:    Apache-2.0

URL:        https://github.com/onnx/onnx
Source0:    https://github.com/onnx/onnx/archive/v%{version}/%{name}-%{version}.tar.gz

BuildRequires:  cmake >= 3.13
BuildRequires:  make
BuildRequires:  findutils
BuildRequires:  zlib-devel
BuildRequires:  python-devel
BuildRequires:  python%{pyver}dist(pip)
BuildRequires:  python%{pyver}dist(protobuf)
BuildRequires:  python%{pyver}dist(pytest)
BuildRequires:  python%{pyver}dist(pybind11)
BuildRequires:  cmake(pybind11)
BuildRequires:  protobuf-devel

%patchlist
# Build shared libraries and fix install location 
https://src.fedoraproject.org/rpms/onnx/raw/rawhide/f/0000-Build-shared-libraries-and-fix-install-location.patch
# Use system protobuf and require parameterized
https://src.fedoraproject.org/rpms/onnx/raw/rawhide/f/0002-Use-system-protobuf-and-require-parameterized.patch
# Add fixes for use with onnxruntime
https://src.fedoraproject.org/rpms/onnx/raw/rawhide/f/0004-Add-fixes-for-use-with-onnxruntime.patch
# Also for onnxruntime, see https://github.com/microsoft/onnxruntime/issues/24561
https://github.com/microsoft/onnxruntime/raw/refs/heads/main/cmake/patches/onnx/onnx.patch
# Fix linkage
onnx-absl-linkage.patch

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
sed -r \
    -e 's/--nbval //' \
    -e 's/--nbval-current-env //' \
    -i pyproject.toml

# Make absl Great Again
sed -i -e 's,CMAKE_CXX_STANDARD 17,CMAKE_CXX_STANDARD 20,g' CMakeLists.txt

%build
%cmake \
    -DONNX_USE_LITE_PROTO=OFF \
    -DONNX_USE_PROTOBUF_SHARED_LIBS=ON \
    -DCMAKE_SKIP_RPATH:BOOL=ON \
    -DBUILD_ONNX_PYTHON:BOOL=ON \
    -DPY_SITEARCH=%{python3_sitearch} \
    -G Ninja
# Generate protobuf header and source files
#ninja_build gen_onnx_proto
# Build
%ninja_build

cd ..
# Build python libs
%py_build

%install
%ninja_install -C build
# Need to remove empty directories
find "%{buildroot}/%{_includedir}" -type d -empty -delete
find "%{buildroot}/%{python3_sitearch}" -type d -empty -delete
# Install *.proto files
install -p "./onnx/"*.proto -t "%{buildroot}/%{_includedir}/onnx/"

%py_install

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
%{python3_sitearch}/onnx-%{version}.dist-info
