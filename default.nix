let
  sources = import ./nix/sources.nix;
  pkgs = import sources.nixpkgs { };
  pythonPkgs = pkgs.python3Packages;
in pythonPkgs.buildPythonPackage rec {
  pname = "org-todoist";
  version = "1.0";

  src = ./.;

  doCheck = false;

  buildInputs = with pythonPkgs; [ black pylint mypy ];
  propagatedBuildInputs = [ pythonPkgs.todoist ];
}
