## Plutus data CBOR generator

This is a utility package that generates CBOR hex for any Plutus 
data, including datum and redeemer. We use this it to generate some ground truth values 
for some plutus tests.

### How to use

1. Install [nix](https://nixos.org/download.html)
2. Clone [plutus-apps](https://github.com/input-output-hk/plutus-apps).
3. Inside `plutus-apps`, start a nix shell with command `nix-shell`.
4. Change directory to the parent folder of this README file. 
5. Modify file `src/PlutusData.hs` to create data structures you are interested in.
6. Run `cabal run PlutusData`, and the cbor of your target data structure will be written to `plutus-data.cbor`.


Some part of the source code is copied from [Deploy.hs](https://github.com/input-output-hk/plutus-pioneer-program/blob/79b0816b6f84f171c8f01073e5445033869c41b7/code/week03/src/Week03/Deploy.hs) 
in plutus-pioneer-program.