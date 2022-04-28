# FortyTwo

This example implements the off-chain code of forty-two, a sample program in week2 of Plutus-Pioneer-Program. 
The original Plutus script cound be found [here](https://github.com/input-output-hk/plutus-pioneer-program/blob/6be7484d4b8cffaef4faae30588c7fb826bcf5a3/code/week02/src/Week02/Typed.hs).
The compiled Plutus core cbor hex is stored in file [fortytwo.plutus](fortytwo.plutus) in this folder.

FortyTwo is a simple smart contract that could be unlocked only by a redeemer of Integer value 42.
[forty_two.py](forty_two.py) contains the code of two transactions: 1) a giver sending 10 ADA to a script address, 
and 2) a taker spend the ADA locked in that script address. 

Below is the visualization of the lifecycle of UTxOs involved:


```
 
                   Giver Tx                                           Taker Tx
                 ┌-----------┐                            ┌-----------------------------┐  
                 |           |                            |                             |                          
                 |  Spend    |                            |  Spend with Redeemer (42)   |                          
  UTxO (X ADA) ━━━━━━━┳━━━━━━━━━ Script UTxO (10 ADA) ━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━ UTxO (5 ADA)           
                 |    ┃      |                            |                 ┃           |                          
                 |    ┗━━━━━━━━━ Change UTxO (X-10 ADA)   |                 ┗━━━━━━━━━━━━━━ Change UTxO (~4.7 ADA) 
                 |  Tx Fee   |                            |                             |                          
                 |(~0.16 ADA)|                            |                             |
                 |           |      Taker's Collateral ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Taker's Collateral 
                 └-----------┘          UTxO (5 ADA)      |                             |     UTxO (5 ADA)                                                  
                                                          |      Tx fee (~0.3 ADA)      |                           
                                                          └-----------------------------┘

                                                                        
```