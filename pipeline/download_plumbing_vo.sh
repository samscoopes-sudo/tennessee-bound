#!/bin/bash
set -e
OUTDIR="/workspace/tennessee-bound/pipeline/channels/tennessee-bound/runs/plumbing-tips"
mkdir -p "$OUTDIR"
cd "$OUTDIR"

echo "Downloading plumbing VO chunks..."

curl -sL -o chunk0.mp3 \
  "https://ai-voiceovers.s3.us-east-1.amazonaws.com/61226c58-2605-4e44-ab0d-31d4d54160fd/baf44eb8-0381-4e7b-b8c3-2d0af806ae03.mp3?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAQLTYEZQZ77K5BQJ4%2F20260827%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260827T181400Z&X-Amz-Expires=43200&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEHMaCXVzLWVhc3QtMSJHMEUCIApT6bIiZ5fzN61Kj5ux0mZQ0G3oc971w7l3LFE0roGaAiEAwsEJ4Bbb2FHBQve5cIEYlaWjtObagfyZ%2B2%2B13NPWIoUqgAUIOxAAGgwwMjQ5NDgwMzQ2MTEiDMio0LdeQDWcb29S%2BCrdBM6wq0zXvfr2IUWVe7X4aIQtJ1NcOLImbFFv4SQdzKgFf22seQPllDcl5whMPRqtECMmBvzTbncrF3yxLMsHKAenK3U%2BlQv%2FMDS9D1aBtuMqCmxaOlh0fGyFZJmv4e34M0EqEacLZDFgBIRmoBkffJF%2BuzlR6hU9%2FXDH1CXwa%2Fz7j0vPJUO%2FMnVtlL2U95HGRqkRApQFutP9vSZ8h5P7M8Xewwom4TxG9Qxy0ITwknanBM0DEJGNYifW2yK12%2FpCkwIePjN0Z%2Fl50NDXzYvGRCL5TAjJFCKVBD4nAg4MzTBMI%2B0Pr5qcBGT8LOQfySInMRAqHLylaX6LAzy5YZahTXnUy%2FWVnoUHKRQ8t5Y6goczJsnIchHXfmRoMQqJD7jdbZLsR2F%2BxV9dnBFdHcGMgM9%2FQbNh%2FWS2%2Fze9ijzpaYWCmC7UdORs2ZmncxBmz0TrGuQ1xMeoedslHMaIKT98XoVqe3Xt%2BSXXbw6mKxc17YVRf1BzAUT%2BDKAgq2BWUemx3ZY%2BGX0vQZGH7plxEseZytge7wzhRAddK1Dg9JVGhdAdDWc6syrFgAIs6fNXEJ3%2BlbuYCrMZuhIg55xixLbpTranTwIZE%2BkDQ%2BKGUXHGGAB9NbahwQHsDMo1MwpLROyAv%2B9yw6q6G6SXH0rt0xdhie1cddm9Xc8TNQRlA1k2hSwz68ZkZ4T0ThS9cUamoKQ3AW%2B3KVrgcgr8hZd77u5oCjkhoFtauQx0mIt6EDKT%2FZqAqayJDCkuxhlReuPsrrdY%2BVxnIrzA%2BGUV4BA8Nyhs2HS3cDuqvmY3rXBJZXUPMOj8wdQGOpgBiHNSHzeMbUp6PQ0YiHy8ZLiHvOoWprQdTijBsteHjIXlV70S082eN2DAJ1c56Qz1h3rxYhY2Es%2FpC%2FCaWLZqN%2BDnxbUnSFJOC6aOFmldsciartEI4LfvKw9AQayzBMIBNl3dSE2ox14x%2BzavQhdgnynrgFepL%2BnxEtsIqrz6hq8lnHNBwHH%2FCTyN94nKaUvz160ncWmKvHo%3D&X-Amz-Signature=6ef6e847d30918b64140be3bb3beff07ef6b0c582d144c8ea1baffdf15c6fecf&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject"
echo "chunk0 done"

curl -sL -o chunk1.mp3 \
  "https://ai-voiceovers.s3.us-east-1.amazonaws.com/61226c58-2605-4e44-ab0d-31d4d54160fd/1bd487d5-1aac-46ba-bab2-1e63b1e25345.mp3?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Credential=ASIAQLTYEZQZYL3C4KGZ%2F20260827%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260827T181624Z&X-Amz-Expires=43200&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEHMaCXVzLWVhc3QtMSJHMEUCIDCFnhEK3uhASkfyfYnYMKEVUWAv%2F6rIurtj9WK%2BHmsjAiEAmgH9%2B4v55XzXKq82lXt5KjhyhxTobKyhv4nqZa61Q3QqgAUIOxAAGgwwMjQ5NDgwMzQ2MTEiDFu8%2FQOa4Df8Nvz0WCrdBMkS2BlFGnKBULAYEYGMZN2v0qgWW9WVk5pH79Pv6%2F950cSRlyR%2FGsIxed4mISaW1PoGoQFV3%2B5wvX7pPNHK42qkix9I2wval7%2BSOhN5JcZwcTR627PqwbjaYil8gTSIcG1i%2BwYIISs7Tp36funk8iPDa69NATtk6cNUp9T1%2FeynCW6d6EX69P2ju2tkQK6JvzEjw3jlMVrpCg8FPZM2iasktnWhcbFjB11b1X%2FyRC%2BEoKPwIiZovyMuR7yMVukAmLAHPXwyNO215TBKtIvqzW15HgMQhVOIZSvOXY%2BDz6kjGIKasn8bZSIIU8KFkRZUInwBnqUZGtEKKtR3GMFl4y2E%2B1Ln0IcD4z%2Bo%2BJnNbua3MrxvoeKZAa6Fg1xHhFtHVDpDw2AIcVuvcJNo%2BITOzLjFkE80JouFp7045YfTnK1%2FV9LXaRZssH0ayKB6r1Z0wfE7vRRgG%2FO9hWjll%2FtRzNLnvRLIkE4fBGHLvwXr8SdxNCZCZlw%2BMxreiB4Nw4Un4ap9v7uziLPVlz4qC2c%2Fk%2F%2Bn61vt5iXXwz00NpxJz82R63m2IbYzgR1K6XNw8LNfmllXx7WiS0zSIrsouPd5NF3eIED0EBuQSH6olcOs73I6ak2dA2rwWGIVV5O%2BBoUjnahbcgNDP7%2BnDucPifoaNXayyLeb7yMPrAOBS%2FnwiKbxFP5eE6whb%2B5POJq10MSWbZRypUrl88YJfi84Rhn0N9y2uuYMNkjwNkheKvVSCcS9wHCUpz7qDpu6%2BRlgG4MkiLj1VuEED%2F4xeSCMnwE%2Bu2VY0yubsuz%2F7DtBW8zcMPj9wdQGOpgBjbEQvYm4GIW0dbJvwIYl5Rm3dixjAZggh4V1mIQY9VEjvbrvIqkwDRP9q9Q8If5z7YLi08V%2FvMXTIZ4bFNa9U4g94UfezfbQggHDxGuYzG7kelQIsJMgVLxv2fZTaxaKvAPZXkl1YAbl8t4jlZnGgtM5vt%2Bm3Z2JcIqqmWV%2BVmecXwxfHzWbJE%2F5skmn7y7gjsqZwJJ9vDg%3D&X-Amz-Signature=139371351c141e73b60df9da5ee517782619221150fd595c69137975d950415e&X-Amz-SignedHeaders=host&x-amz-checksum-mode=ENABLED&x-id=GetObject"
echo "chunk1 done"

echo "Concatenating into vo.wav..."
pip install -q pydub 2>/dev/null
python3 -c "
from pydub import AudioSegment
import glob
chunks = sorted(glob.glob('chunk*.mp3'))
combined = AudioSegment.empty()
for c in chunks:
    seg = AudioSegment.from_mp3(c)
    combined += seg
    print(f'  {c}: {len(seg)/1000:.1f}s')
combined.export('vo.wav', format='wav')
print(f'vo.wav created: {len(combined)/1000:.1f}s ({len(combined)/1000/60:.1f} min)')
"
echo "Done!"
