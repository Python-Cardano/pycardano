# Change Log
All notable changes to this project will be documented in this file.
 
The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).


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