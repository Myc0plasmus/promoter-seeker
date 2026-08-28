{ pkgs ? import <nixpkgs> {}}:
let
  fhs = pkgs.buildFHSEnv rec{
    name = "cardio-challenge-2026";

    targetPkgs = _: [
      pkgs.stdenv.cc.cc
      pkgs.zlib
      pkgs.glib
      pkgs.libGL
      pkgs.glibc
    ];

  };
in fhs.env
