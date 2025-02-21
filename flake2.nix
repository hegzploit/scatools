    {
    description = "ChipWhisperer";
    inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-24.11";
    inputs.nixpkgs-unstable.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    inputs.flake-utils.url = "github:numtide/flake-utils";

    outputs = { self, flake-utils, nixpkgs, nixpkgs-unstable }:
    flake-utils.lib.eachSystem [ flake-utils.lib.system.x86_64-linux ] (system: let
    pkgs = nixpkgs.legacyPackages.${system};
    pkgsUnstable = nixpkgs-unstable.legacyPackages.${system};

      chipwhisperer = pkgs.python3Packages.buildPythonPackage rec {
          pname = "chipwhisperer";
          version = "5.7.0";
          src = pkgs.fetchPypi {
            inherit pname;
            inherit version;
            sha256 = "sha256-xTRUkdo09xKIEGITmEEHSVBd7cqrtD72lR/kklSt7Z8=";
          };
          buildInputs = with pkgs; [
            python312Packages.configobj
            python312Packages.tqdm
            python312Packages.numpy
            python312Packages.fastdtw
            python312Packages.pyserial
            python312Packages.libusb1
            python312Packages.ecpy
            python312Packages.cython
          ];
      };
      datashader = pkgs.python312Packages.datashader.overrideAttrs (old: { doChek = false; });

      #myShell = import ./shell.nix { inherit pkgs pkgsUnstable; };
      myShell = pkgs.mkShell rec {
        nativeBuildInputs = with pkgs; [
	  bash
      gdb
      lcov
      pkg-config
      libffi
      gdbm
      xz
      ncurses5
      readline
      sqlite
      openssl
      tk
      libuuid
      zlib
      zlib-ng
      curl
      libusb1
      usbutils
      gnumake
      #avrlibc
      git
      jupyter
      python312
      python312Packages.configobj
      python312Packages.pip
      python312Packages.bokeh
      python312Packages.cycler
      #python312Packages.datashader
      python312Packages.notebook
      python312Packages.jupyter-client
      python312Packages.jupyter-core
      #python312Packages.nbparameterise
      python312Packages.pandas
      python312Packages.holoviews
      python312Packages.matplotlib
      python312Packages.plotly
      python312Packages.pyyaml
      python312Packages.tqdm
      python312Packages.pycryptodome
      python312Packages.terminaltables
      #python312Packages.phoenixAES
      python312Packages.ipywidgets
      python312Packages.nbconvert
      python312Packages.numpy
      python312Packages.fastdtw
      python312Packages.pyserial
      python312Packages.libusb1
      python312Packages.ecpy
      python312Packages.cython
      libusb1
      chipwhisperer
      python312Packages.h5py
      python312Packages.scipy
      gcc-arm-embedded
        ];
      };

    in rec {
      devShells.default = myShell;
      defaultPackage = devShells.default;
    });

    }

