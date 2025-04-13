#!/bin/bash
# Script to ensure cbor2 is installed with pure Python implementation

set -e

# Check if poetry is available, otherwise use python directly
if command -v poetry &> /dev/null; then
    PYTHON="poetry run python"
else
    PYTHON="python"
fi

echo "Checking cbor2 version..."
$PYTHON -c "from importlib.metadata import version; print(version('cbor2'))" > .cbor2_version
CBOR2_VERSION=$(cat .cbor2_version)
echo "Found cbor2 version: $CBOR2_VERSION"

echo "Checking cbor2 implementation..."
$PYTHON -c "
import cbor2, inspect, sys
decoder_path = inspect.getfile(cbor2.CBORDecoder)
using_c_ext = decoder_path.endswith('.so')
print(f'Implementation path: {decoder_path}')
print(f'Using C extension: {using_c_ext}')
sys.exit(1 if using_c_ext else 0)
"

if [ $? -ne 0 ]; then
    echo "Reinstalling cbor2 with pure Python implementation..."
    $PYTHON -m pip uninstall -y cbor2
    CBOR2_BUILD_C_EXTENSION=0 $PYTHON -m pip install --no-binary cbor2 "cbor2==$CBOR2_VERSION" --force-reinstall
    echo "Successfully reinstalled cbor2 with pure Python implementation"
else
    echo "Already using pure Python implementation of cbor2"
fi

# Clean up
rm -f .cbor2_version 