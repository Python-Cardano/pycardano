## Overview

Runtime environments for integration tests.

`docker-compose.yml` kicks off two components, [cardano-node](https://github.com/input-output-hk/cardano-node) and 
[ogmios](https://github.com/CardanoSolutions/ogmios), which are necessary to run deterministic integration tests.

Good things about a customizable and deterministic ledger:

* Deterministic UTxO set and deterministic actors (isolation).
* Deterministic fees.
* Flexible configurations.
* Reproducible.

To achieve a relatively good degree of determinism, we use a local cardano node that runs as a single 
BFT node in the network. The node will produce all blocks and the environment/ledger is isolated.

## Instructions

### Pre-requisites

* Install [Docker](https://www.docker.com/)

### Launch containers

Bootstrap config files for a single BFT node:

`./bootstrap.sh local-alonzo`


Compose docker services (node + ogmios):

`docker-compose up -d`


Clean up docker containers and volumes when done with testing:

`docker-compose down`


### Test

Current, all integration tests could be kicked off by running:

`./run_tests.sh`