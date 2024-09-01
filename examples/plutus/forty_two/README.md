# FortyTwo

This example implements the off-chain code of forty-two v2 in Plutus. 

FortyTwo is a simple smart contract that could be unlocked only by a redeemer of Integer value 42.
[forty_two.py](forty_two.py) contains the code of three transactions: 
  1) a giver creates an inline script and send it to herself, which cannot be spent by anybody else 
  2) the giver send some ADA to script address
  3) the taker spend the script address with a redeemer of 42 and a reference to the inline script 

Below is the visualization of the lifecycle of UTxOs involved. The entity enclosed in the parenthesis is the owner of the UTxO.

```
                                                                                                
   ┌─────────────────────────────────────────────────────────────────────────┐                  
   │                                                                         │                  
   │  ┌─────────────────────────┐       ┌─────────────────────────┐          │                  
   │  │                         │       │                         │          │                  
   │  │    Initial UTxO         │       │   Change UTxO           │          │                  
   │  │                         ├──────►│                         │          │                  
   │  │    (Giver)              │       │   (Giver)               │          │                  
   │  │                         │       │                         │          │                  
   │  └────────────┬────────────┘       └─────────────────────────┘          │                  
   │               │                                                         │                  
   │               │                                                         │                  
   │               │                    ┌─────────────────────────┐          │                  
   │               │                    │                         │          │                  
   │               │                    │   Inline script UTxO    │          │                  
   │               └───────────────────►│                         ├────────┐ │                  
   │                                    │   (Giver)               │        │ │                  
   │                                    │                         │        │ │                  
   │   Tx1                              └─────────────────────────┘        │ │                  
   │                                                                       │ │                  
   └───────────────────────────────────────────────────────────────────────┼─┘                  
                                                                           │                    
   ┌────────────────────────────────────────────────────────────────┐      │                    
   │                                                                │      │                    
   │  ┌─────────────────────────┐       ┌─────────────────────────┐ │      │                    
   │  │                         │       │                         │ │      │                    
   │  │    Give UTxO            │       │   Locked UTxO           │ │      │                    
   │  │                         ├──────►│                         │ │      │                    
   │  │    (Giver)              │       │   (Script)              │ │      │                    
   │  │                         │       │                         │ │      │                    
   │  └─────────────────────────┘       └─────────────┬───────────┘ │      │                    
   │                                                  │             │      │                    
   │   Tx2                                            │             │      │                    
   └──────────────────────────────────────────────────┼─────────────┘      │                    
                                                      │                    │                    
                                     ┌────────────────┼────────────────────┼─────────────────┐  
                                     │                ▼                    │                 │  
                                     │  ┌─────────────────────────┐        │                 │  
                                     │  │                         │        │                 │  
                                     │  │   Taken UTxO            │        │                 │  
                                     │  │                         │◄───────┘                 │  
                                     │  │   (Taker)               │                          │  
                                     │  │                         │    Refer to script UTxO  │  
                                     │  └─────────────────────────┘                          │  
                                     │                                                       │  
                                     │                                                       │  
                                     │   Tx3                                                 │  
                                     │                                                       │  
                                     └───────────────────────────────────────────────────────┘  
                                                                                                
```