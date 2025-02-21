{
  description = "A Nix flake for the scatools Python module";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        packages.default = pkgs.python3Packages.buildPythonPackage {
          pname = "scatools";
          version = "0.1";

          src = ./.;

          propagatedBuildInputs = with pkgs.python3Packages; [
            scipy
            numpy
            chipwhisperer
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
      });
}
