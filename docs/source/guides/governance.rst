.. _governance-guide:

==================
Governance Guide
==================

The Voltaire era introduces a decentralized governance system to Cardano, allowing the community to shape the future of the platform. PyCardano provides a complete set of tools to participate in this on-chain governance, from registering as a Delegate Representative (DRep) to proposing and voting on governance actions.

This guide will walk you through a practical example of the governance lifecycle.

----------------
Key Concepts
----------------

Before diving into the code, let's review the core components of Cardano's governance model that we'll be interacting with:

*   **Delegate Representative (DRep):** An on-chain identity that can receive delegated voting power from other ada holders. DReps are responsible for voting on governance actions on behalf of their delegators.
*   **Vote Delegation:** The process by which ada holders assign their voting power to a DRep. This allows them to participate in governance without having to vote on every proposal themselves.
*   **Governance Actions:** Proposals that can be submitted to the chain for a vote. These can range from protocol parameter changes to treasury withdrawals. This guide uses a simple `InfoAction`, which has no on-chain effect but is useful for demonstrating the proposal and voting mechanism.
*   **Voting Procedures:** The act of a DRep (or other voter type) casting a vote (Yes, No, or Abstain) on a specific governance action.

------------------------------------
Governance Tutorial: A Walkthrough
------------------------------------

This tutorial demonstrates a complete governance flow using the example script found at `examples/more_examples/13_governance.py`. We will:

1.  Create and register a DRep.
2.  Delegate voting power from a separate stake key to that DRep.
3.  Propose a new `InfoAction` to the blockchain.
4.  Have the DRep vote on the action.

**Prerequisites**

To follow along, you will need:

*   A `BlockFrostChainContext`, which requires a Blockfrost Project ID. See the :doc:`transaction` guide for setup instructions.
*   A funded wallet with a local `payment.skey` file. The script assumes this key will fund the creation of new addresses required for the tutorial.
*   An environment configured to point to your keys and Blockfrost project ID.

**Step 0: Setup and Initialization**

First, we set up our environment. This includes initializing a `BlockFrostChainContext` to interact with the blockchain and loading our main payment key, which will be used to fund the transactions.

.. code-block:: python

    from pycardano import (
        # Core
        Network,
        BlockFrostChainContext,
        TransactionBuilder,
        # Keys & Addresses
        PaymentSigningKey,
        StakeKeyPair,
        Address,
        # Certificates
        RegDRepCert,
        StakeRegistrationAndVoteDelegation,
        DRepCredential,
        StakeCredential,
        DRep,
        DRepKind,
        # Governance
        GovActionId,
        InfoAction,
        Voter,
        VoterType,
        Vote,
        Anchor,
        AnchorDataHash,
    )

    # Initialize chain context
    network = Network.TESTNET
    context = BlockFrostChainContext("your_blockfrost_project_id", base_url=ApiUrls.preprod.value)

    # Load main payment key and derive address
    main_payment_skey = PaymentSigningKey.load("path/to/payment.skey")
    main_payment_vkey = main_payment_skey.to_verification_key()
    main_address = Address(main_payment_vkey.hash(), network=network)

**Step 1: Creating and Registering a DRep**

Our first on-chain action is to register a new DRep. This requires a new stake key pair that will represent the DRep's identity.

The registration is done via a `RegDRepCert` certificate, which includes the DRep's credential (the hash of its stake verification key), a deposit, and an optional `Anchor` for off-chain metadata.

.. code-block:: python

    # 1.1 Generate or load DRep stake key pair
    drep_stake_key_pair = StakeKeyPair.generate()

    # 1.2 Create DRep address
    drep_address = Address(
        payment_part=main_payment_vkey.hash(),
        staking_part=drep_stake_key_pair.verification_key.hash(),
        network=network,
    )
    # The drep_address must be funded before it can submit the registration.

    # 1.4 Create DRep registration certificate
    drep_credential = DRepCredential(drep_stake_key_pair.verification_key.hash())
    anchor = Anchor(
        url="https://pycardano.drep.example.com/info",
        data_hash=AnchorDataHash(bytes.fromhex("00" * 32)),
    )
    drep_registration_cert = RegDRepCert(
        drep_credential=drep_credential,
        coin=500_000_000, # 500 ADA deposit
        anchor=anchor,
    )

    # 1.5 Build and submit transaction
    builder = TransactionBuilder(context)
    builder.add_input_address(str(drep_address))
    builder.certificates = [drep_registration_cert]
    
    # The transaction must be signed by the payment key controlling the UTxOs
    # and the DRep's stake key to authorize the registration.
    signed_tx = builder.build_and_sign(
        signing_keys=[main_payment_skey, drep_stake_key_pair.signing_key],
        change_address=drep_address,
    )

    context.submit_tx(signed_tx)

**Step 2: Delegating Voting Power to the DRep**

With a registered DRep, other ada holders can now delegate their voting power to it. In this step, we'll create a *new* stake identity for our main wallet and delegate its voting power to the DRep.

We use the powerful `StakeRegistrationAndVoteDelegation` certificate, which handles both stake key registration (and its associated deposit) and vote delegation in a single certificate.

.. code-block:: python

    # 2.1 Generate a new stake key for the main account's voting delegation
    main_voting_stake_key_pair = StakeKeyPair.generate()

    # 2.4 Create StakeRegistrationAndVoteDelegation certificate
    stake_credential = StakeCredential(main_voting_stake_key_pair.verification_key.hash())
    
    # Create a DRep object pointing to the DRep we created in Step 2
    drep_for_delegation = DRep(
        kind=DRepKind.VERIFICATION_KEY_HASH,
        credential=drep_stake_key_pair.verification_key.hash()
    )

    delegation_cert = StakeRegistrationAndVoteDelegation(
        stake_credential=stake_credential,
        drep=drep_for_delegation,
        coin=2_000_000, # 2 ADA stake key registration deposit
    )

    # Build and sign the transaction. The new voting stake key must sign
    # to authorize the delegation.
    builder = TransactionBuilder(context)
    # The address paying for this must contain the new stake part.
    # It must be funded first.
    main_full_address = Address(
        payment_part=main_payment_vkey.hash(),
        staking_part=main_voting_stake_key_pair.verification_key.hash(),
        network=network,
    )
    builder.add_input_address(str(main_full_address))
    builder.certificates = [delegation_cert]

    signed_tx = builder.build_and_sign(
        signing_keys=[main_payment_skey, main_voting_stake_key_pair.signing_key],
        change_address=main_full_address,
    )

    context.submit_tx(signed_tx)


**Step 3: Proposing a Governance Action**

Now, let's propose a governance action. The DRep itself will act as the proposer. Proposing an action requires a deposit, which is returned when the action is finalized.

We use `TransactionBuilder.add_proposal` to construct the proposal, specifying the deposit, a reward account for the deposit's return, the governance action itself (`InfoAction`), and an anchor.

.. code-block:: python

    # 3.2 Create InfoAction
    info_action = InfoAction()

    # 3.3 Define anchor for the proposal
    proposal_anchor = Anchor(
        url="https://pycardano.infoaction.example.com/details",
        data_hash=AnchorDataHash(bytes.fromhex("11" * 32)),
    )

    # 3.4 The reward account for the proposal deposit refund.
    reward_account_address = Address(
        staking_part=drep_stake_key_pair.verification_key.hash(),
        network=context.network
    )

    # 3.5 Build and submit transaction
    builder = TransactionBuilder(context)
    builder.add_input_address(str(drep_address)) # DRep's address pays the proposal deposit
    builder.add_proposal(
        deposit=100_000_000_000, # Example: 100k ADA deposit
        reward_account=bytes(reward_account_address),
        gov_action=info_action,
        anchor=proposal_anchor,
    )

    # Sign with the payment key and the DRep's stake key as the proposer.
    signed_tx = builder.build_and_sign(
        signing_keys=[main_payment_skey, drep_stake_key_pair.signing_key],
        change_address=drep_address,
    )
    context.submit_tx(signed_tx)

    # The GovActionId is derived from the transaction ID and the proposal's index
    gov_action_id = GovActionId(transaction_id=signed_tx.id, gov_action_index=0)


**Step 4: Voting on a Governance Action**

In the final step, our DRep votes on the governance action. A `Voter` object is created to represent the DRep. The vote is then added to a transaction using `TransactionBuilder.add_vote`.

.. code-block:: python

    # 4.2 Create Voter object for the DRep
    drep_voter = Voter(
        credential=drep_stake_key_pair.verification_key.hash(),
        voter_type=VoterType.DREP,
    )

    # 4.3 Reconstruct GovActionId from the previous step
    gov_action_id = GovActionId(
        transaction_id=TransactionId.from_hex("..."), # From Step 4
        gov_action_index=0,
    )

    # 4.5 Build transaction with the vote
    builder = TransactionBuilder(context)
    builder.add_input_address(str(drep_address)) # DRep's address pays for the vote tx
    builder.add_vote(
        voter=drep_voter,
        gov_action_id=gov_action_id,
        vote=Vote.YES,
        anchor=vote_anchor,
    )

    # Sign with the payment key and the DRep's stake key to authorize the vote.
    signed_tx = builder.build_and_sign(
        signing_keys=[main_payment_skey, drep_stake_key_pair.signing_key],
        change_address=drep_address,
    )
    context.submit_tx(signed_tx)

This concludes the basic lifecycle of DRep creation, delegation, and governance participation. You can adapt these patterns to handle other governance actions and more complex scenarios.

----------------
Full Example
----------------

A complete, runnable script demonstrating these steps with helper functions for state management and funding is available at `examples/more_examples/13_governance.py <https://github.com/Python-Cardano/pycardano/blob/main/examples/more_examples/13_governance.py>`_.
