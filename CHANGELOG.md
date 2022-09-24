# Change Log
All notable changes to this project will be documented in this file.
 
The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [0.6.2] - 2022-09-03

Fix dependencies.

## [0.6.1] - 2022-09-03

### Added
- Add coins_per_utxo_size in blockfrost chain context

### Fixed
- Fixed `PPViewHashesDontMatch` issue. See details in [issue 81] (https://github.com/cffls/pycardano/issues/81).


## [0.6.0] - 2022-08-28

`v0.6.0` is update for Vasil hard fork.

### Added
- Support for reference inputs ([CIP31](https://github.com/cardano-foundation/CIPs/tree/master/CIP-0031)).
- Support for inline datum ([CIP32](https://github.com/cardano-foundation/CIPs/tree/master/CIP-0032)).
- Support for reference scripts ([CIP33](https://github.com/cardano-foundation/CIPs/tree/master/CIP-0033)).
- Vasil changes for Ogmios.
- Vasil changes for blockforst.
- Add type "RawPlutusData", which is used as the default type for datum deserialized from cbor.
- `TransactionOutput` now has two new fields, `datum` and `script`, which could be added to the transaction output.
- Blockfrost chain context now supports custom API url.

## Changed
- Improved the format of transaction representation.
- Method `add_script_input` in `TransactionBuilder` no longer requires `script` field to be set.
If absent, the transaction builder will try to find it from chain context.
- Similarly, method `add_minting_script` in `TransactionBuilder` no longer requires `script` field to be set.
If absent, the transaction builder will try to find it from chain context.

## [0.5.1] - 2022-07-09

### Added

- Policy json serializer ([#58](https://github.com/cffls/pycardano/pull/58)) 

### Fixed

- Fix min lovelace when the input is Value type


## [0.5.0] - 2022-06-15

### Added

- Staking certificates.
- Add an option to merge change into already existing output. ([#38](https://github.com/cffls/pycardano/pull/38)).
- Enable UTxO query with Kupo ([#39](https://github.com/cffls/pycardano/pull/39)).
- Add 'add_minting_script' to txbuilder.
- Add usage guides for Plutus ([#46](https://github.com/cffls/pycardano/pull/46)).
- Add message signing and verification (CIP8) ([#45](https://github.com/cffls/pycardano/pull/45)).

### Changed

- `amount` in `TransactionOutput` will be converted to type `Value` even when an `int` is passed in ([#42](https://github.com/cffls/pycardano/pull/42)).
- Add unknown fields to ArraySerializable if more values are provided.

### Fixed

- Prevent 'Transaction.from_cbor' from dropping data in datum.
- Add fake fee to fake transaction when fee is 0.

## [0.4.1] - 2022-05-03

### Changed

- Use specific version of blockfrost-python

### Fixed

- Don't add min_lovelace to unfulfilled_amount when change address is not provided


## [0.4.0] - 2022-04-29

### Added

- Support mint redeemer
- Add execution units estimation
- Fee Estimation Improvement ([#27](https://github.com/cffls/pycardano/pull/27))
- Add blockfrost support for transaction evaluation

### Changed

- Refactor transaction builder to a dataclass
- Upgrade Blockfrost to 0.4.4

### Fixed

- Do not modify multiassets when being added or subtracted
- Restore empty datum in redeemer



## [0.3.1] - 2022-03-31

Some minor improvements in transaction builder.

### Added

- Add more details to the message of expection when UTxO selectors failed.
- Validate output value is non-negative.



## [0.3.0] - 2022-03-21

### Added

- Incorporate change split logic [#7](https://github.com/cffls/pycardano/pull/7).
- Plutus
  - Datum support for transaction inputs and transaction outputs.
  - New function `add_script_input` in tx builder to support spending of Plutus script input.
  - Add collateral to tx builder for script transaction.
  - Add `plutus_script_hash` that calculates the hash of a Plutus script.
  - Include script execution steps and memory into fee calculation.
- Add `build_and_sign` to tx builder.

### Changed

- Remove positional argument `index` from Redeemer's constructor. 



## [0.2.0] - 2022-03-13

This release added essential features for Plutus script interactions.

### Added

- Plutus data
  - Serialization, deserialization, and customization of plutus data and redeemer
  - Plutus cost model
  - Calculation of script data hash
  - JSON compatibility
- Extended key support

### Changed

- Sort multi-assets based on policy id and asset names

### Fixed

- Fail tx builder when input amount is not enough to cover outputs and tx fee 


 
## [0.1.2] - 2022-02-20
   
### Added

- Metadata and native script to docs
- A full stack example (flask + PyCardano + BlockFrost + React + Nami wallet)
- Continuous integration
- Ogmios backend support

### Changed

 
### Fixed

- Minor fix in native token example