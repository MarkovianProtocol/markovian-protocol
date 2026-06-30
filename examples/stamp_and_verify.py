#!/usr/bin/env python3
"""
Markovian quickstart: stamp an agent's prediction, then verify it.

The point of this example is the one thing subjective ratings cannot do:
commit a prediction BEFORE the outcome is known, so the track record cannot
be edited in hindsight. That is the difference between a record that is
"recorded" and one that is "unfakeable."

No account. No wallet. No token. Runs against the public chain in seconds.

    pip install markovian
    python examples/stamp_and_verify.py
"""

import json
from markovian import MarkovianClient


def main():
    client = MarkovianClient()  # free tier, no API key

    # 1. An agent makes a prediction. Commit it now, before the event resolves.
    prediction = {
        "agent": "forecaster-v1",
        "claim": "QQQ closes the week in MARKUP regime",
        "as_of": "before the close",
    }
    payload = json.dumps(prediction, sort_keys=True)

    receipt = client.stamp(payload, label="prediction:forecaster-v1")
    root = receipt["merkle_root"]

    print("STAMPED. This prediction is now committed and cannot be backdated.")
    print(f"  merkle_root : {root}")
    print(f"  block       : {receipt['block_height']}")
    print(f"  mkv_burned  : {receipt['mkv_burned']}   (the basic stamp is free)")
    print(f"  verify_url  : {receipt['verify_url']}")
    print()

    # 2. Anyone can verify it. No SDK, no account. Trust no one.
    result = client.verify(root)
    print(f"VERIFIED: {result['verified']}")
    print()
    print("A stranger can confirm the same thing with nothing but curl:")
    print(f"  curl {receipt['verify_url']}")


if __name__ == "__main__":
    main()
