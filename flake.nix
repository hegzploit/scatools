{
  description = "A Nix flake for the scatools Python module and ChipWhisperer integration";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs";
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs-unstable.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
  };

  outputs = { self, flake-utils, nixpkgs, nixpkgs-unstable }:
    flake-utils.lib.eachSystem [ "x86_64-linux" ] (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        pkgsUnstable = nixpkgs-unstable.legacyPackages.${system};

        chipwhisperer = pkgs.python3Packages.buildPythonPackage rec {
          pname = "chipwhisperer";
          version = "5.7.0";
          src = pkgs.fetchPypi {
            inherit pname version;
            sha256 = "sha256-xTRUkdo09xKIEGITmEEHSVBd7cqrtD72lR/kklSt7Z8=";
          };
          buildInputs = with pkgs.python312Packages; [
            configobj
            tqdm
            numpy
            fastdtw
            pyserial
            libusb1
            ecpy
            cython
          ];
        };

        packages.default = pkgs.python3Packages.buildPythonPackage {
          pname = "scatools";
          version = "0.1";

          src = ./.;

          propagatedBuildInputs = with pkgs.python3Packages; [
            scipy
            numpy
            (pkgs.callPackage chipwhisperer {})
            matplotlib
            plotly
            pandas
            tqdm
          ];

          meta = with pkgs.lib; {
            description = "A collection of tools for side-channel analysis";
            homepage = "https://hegz.io";
            license = licenses.mit;
            maintainers = [ "Hegz <y@hegz.io>" ];
          };
        };

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
            git
            jupyter
            python312
            python312Packages.configobj
            python312Packages.pip
            python312Packages.bokeh
            python312Packages.cycler
            python312Packages.notebook
            python312Packages.jupyter-client
            python312Packages.jupyter-core
            python312Packages.pandas
            python312Packages.holoviews
            python312Packages.matplotlib
            python312Packages.plotly
            python312Packages.pyyaml
            python312Packages.tqdm
            python312Packages.pycryptodome
            python312Packages.terminaltables
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
      in
      {
        packages = {
          default = packages.default;
        };
        devShells = {
          default = myShell;
        };
      }
    );
}
