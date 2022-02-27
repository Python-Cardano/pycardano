{-# LANGUAGE DataKinds             #-}
{-# LANGUAGE MultiParamTypeClasses #-}
{-# LANGUAGE OverloadedStrings     #-}
{-# LANGUAGE ScopedTypeVariables   #-}
{-# LANGUAGE TemplateHaskell       #-}


module Main where

import           Data.Aeson           (encode)
import qualified Data.ByteString.Lazy  as LBS
import qualified PlutusTx
import PlutusTx.Prelude ( Integer, (.), BuiltinByteString, )
import Ledger ( PaymentPubKeyHash(PaymentPubKeyHash), POSIXTime )
import           Prelude              (IO, Show (..), FilePath)

writeCBORToPath :: PlutusTx.ToData a => FilePath -> a -> IO ()
writeCBORToPath file = LBS.writeFile file . encode . PlutusTx.toData


data Test = Test
    {
        a :: !Integer,
        b :: !BuiltinByteString
    } deriving (Show)

PlutusTx.makeLift ''Test
PlutusTx.makeIsDataIndexed ''Test [('Test, 130)]


data BigTest = BigTest Test | LargestTest deriving (Show)

PlutusTx.makeLift ''BigTest
PlutusTx.makeIsDataIndexed ''BigTest [('BigTest, 8), ('LargestTest, 9)]

data VestingParam = VestingParam
    { beneficiary :: PaymentPubKeyHash
    , deadline    :: POSIXTime
    , testa       :: BigTest
    , testb       :: BigTest
    } deriving (Show)

PlutusTx.makeLift ''VestingParam

PlutusTx.makeIsDataIndexed ''VestingParam [('VestingParam, 1)]

test :: Test
test = Test
    { a = 123
    , b = "1234"
    }

param :: VestingParam
param = VestingParam
    { beneficiary = Ledger.PaymentPubKeyHash "c2ff616e11299d9094ce0a7eb5b7284b705147a822f4ffbd471f971a"
    , deadline    = 1643235300000
    , testa       = BigTest test
    , testb       = LargestTest
    }

main :: IO ()
main = writeCBORToPath "plutus-data.cbor" param
