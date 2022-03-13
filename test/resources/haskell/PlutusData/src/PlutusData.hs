{-# LANGUAGE DataKinds             #-}
{-# LANGUAGE MultiParamTypeClasses #-}
{-# LANGUAGE OverloadedStrings     #-}
{-# LANGUAGE ScopedTypeVariables   #-}
{-# LANGUAGE TemplateHaskell       #-}


module Main where

import           Cardano.Api
import           Data.Aeson           (encode)
import qualified Data.ByteString.Lazy  as LBS
import qualified Data.ByteString.Lazy.Char8 as C
import           PlutusTx              (Data (..))
import qualified PlutusTx
import qualified PlutusTx.AssocMap as AssocMap
import PlutusTx.Prelude ( BuiltinByteString, )
import Ledger ( PaymentPubKeyHash(PaymentPubKeyHash), POSIXTime )

writeCBORToPath :: PlutusTx.ToData a => FilePath -> a -> IO ()
writeCBORToPath file = LBS.writeFile file . encode . PlutusTx.toData

printCBOR :: PlutusTx.ToData a => a -> IO ()
printCBOR = putStrLn . C.unpack . encode . PlutusTx.toData

dataToScriptData :: Data -> ScriptData
dataToScriptData (Constr n xs) = ScriptDataConstructor n $ dataToScriptData <$> xs
dataToScriptData (Map xs)      = ScriptDataMap [(dataToScriptData x, dataToScriptData y) | (x, y) <- xs]
dataToScriptData (List xs)     = ScriptDataList $ dataToScriptData <$> xs
dataToScriptData (I n)         = ScriptDataNumber n
dataToScriptData (B bs)        = ScriptDataBytes bs

toJSONByteString :: PlutusTx.ToData a => a -> LBS.ByteString
toJSONByteString = encode . scriptDataToJson ScriptDataJsonDetailedSchema . dataToScriptData . PlutusTx.toData

printJSON :: PlutusTx.ToData a => a -> IO ()
printJSON = putStrLn . C.unpack . toJSONByteString

writeJSON :: PlutusTx.ToData a => FilePath -> a -> IO ()
writeJSON file = LBS.writeFile file . toJSONByteString


data Test = Test
    {
        a :: !Integer,
        b :: !BuiltinByteString,
        c :: !([Integer]),
        d :: !(AssocMap.Map Integer BuiltinByteString)
    }
    deriving (Show)

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
    , c = [4, 5, 6]
    , d = AssocMap.fromList [(1, "1"), (2, "2")]
    }

param :: VestingParam
param = VestingParam
    { beneficiary = Ledger.PaymentPubKeyHash "c2ff616e11299d9094ce0a7eb5b7284b705147a822f4ffbd471f971a"
    , deadline    = 1643235300000
    , testa       = BigTest test
    , testb       = LargestTest
    }

main :: IO ()
main = do
    putStrLn "Plutus data cbor:"
    printCBOR param
    writeCBORToPath "plutus-data.cbor" param

    putStrLn "Plutus data json:"
    printJSON param
    writeJSON "plutus-data.json" param
