<!-- codex-review: model=gpt-6.1-terra -->

No findings beyond the approved retirement of R1 and its waiver.

All four requested self-tests passed:

- `check-ask-store.py`: 139/139 and 30/30 cannot-run cases.
- `check-merge-ready.py`: 462/462.
- `gen-dashboard.py`: 331/331.
- `check-shipping-sets.py`: 170/170.

The two L1 mutations, the C1 replay removal, and restoration of F4’s early return each failed their named new case in scratch copies. The replay case also requires exactly two commands, so an absent or renamed step returning an empty list fails. F3’s references were updated, with the component ID retained and annotated as intended.

The R1-related answers below record the literal behavior change required by the flagged-line format; that change is approved.

## Loosening answers
LOOSENING-CHECK e6e8be282e2a: not a loosening
LOOSENING-CHECK 62698a2e9b71: not a loosening
LOOSENING-CHECK da70dc09647e: not a loosening
LOOSENING-CHECK 13be0240fb61: not a loosening
LOOSENING-CHECK 0d8310068739: not a loosening
LOOSENING-CHECK fe25efe81241: not a loosening
LOOSENING-CHECK 0ec5b58a4a23: not a loosening
LOOSENING-CHECK 613b1f251156: not a loosening
LOOSENING-CHECK cbcd8e87b59d: not a loosening
LOOSENING-CHECK d8cb883c1e49: not a loosening
LOOSENING-CHECK 3ca788a8644e: not a loosening
LOOSENING-CHECK 9672ef5a0592: not a loosening
LOOSENING-CHECK aff75c7dfe10: not a loosening
LOOSENING-CHECK 430752de2cdb: not a loosening
LOOSENING-CHECK eb9ef5d6a7d9: not a loosening
LOOSENING-CHECK c30147342858: not a loosening
LOOSENING-CHECK 1f5976beb765: not a loosening
LOOSENING-CHECK 464185338bed: not a loosening
LOOSENING-CHECK 47453303e1f5: not a loosening
LOOSENING-CHECK 46206c617548: not a loosening
LOOSENING-CHECK 363e65f6a8ae: not a loosening
LOOSENING-CHECK 3333fd147295: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK 7d6a9de7ad21: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK 8aa95199fe1b: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK 943277c7a07d: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK bde3e64cd673: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK 73671d145855: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK c126a60b4c86: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK 1b47be859cd1: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK ad9516c39d3e: finding: a code change with an empty NO-ENTRY declaration now passes
LOOSENING-CHECK eb5f200c43ba: finding: a code change with an empty NO-ENTRY declaration now passes
LOOSENING-CHECK 84ccf5a8e964: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK 3205dd2c926a: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK 0a4df03e5f2c: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK 69674994bac8: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK 2142e6e7c368: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK f50d8455768d: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK 279caa183a8c: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK cb289bda54e5: not a loosening
LOOSENING-CHECK c2066e2a549d: not a loosening
LOOSENING-CHECK a8edc9f9f098: finding: a code change with an empty NO-ENTRY declaration now passes
LOOSENING-CHECK 8e0d21430c5b: not a loosening
LOOSENING-CHECK 2e9733955a6d: not a loosening
LOOSENING-CHECK 50d736899fec: not a loosening
LOOSENING-CHECK 15b3ce29e5a5: not a loosening
LOOSENING-CHECK dd75b477d84d: not a loosening
LOOSENING-CHECK 505b491bf89a: not a loosening
LOOSENING-CHECK 0f26969699dc: not a loosening
LOOSENING-CHECK 8c4f23970180: not a loosening
LOOSENING-CHECK ada05f960979: not a loosening
LOOSENING-CHECK 38d32f7744d2: not a loosening
LOOSENING-CHECK 7b36eea5210f: not a loosening
LOOSENING-CHECK c4a68d40a51b: not a loosening
LOOSENING-CHECK eae32eae0236: not a loosening
LOOSENING-CHECK 5bb97df80fa6: not a loosening
LOOSENING-CHECK 3734bc6d3216: not a loosening
LOOSENING-CHECK 09655660aa41: not a loosening
LOOSENING-CHECK 3a6fadefb326: not a loosening
LOOSENING-CHECK c60b81955793: not a loosening
LOOSENING-CHECK 32a0bb42612b: not a loosening
LOOSENING-CHECK 4b3ba92889df: not a loosening
LOOSENING-CHECK a7fdb5b07bc6: not a loosening
LOOSENING-CHECK 0b639f290178: not a loosening
LOOSENING-CHECK aacc40ab275d: not a loosening
LOOSENING-CHECK 63f02e314cb6: not a loosening
LOOSENING-CHECK de698cafded8: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK 5792d2b53b82: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK 85dd37c47b83: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK 24884c9db566: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK 40a639481f0e: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK 188d2e869d21: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK 9dfacba439cd: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK 9f02b12aefce: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK 3c3091307a87: not a loosening
LOOSENING-CHECK a37dc69d3ebe: not a loosening
LOOSENING-CHECK ac5e7ae1f0d8: not a loosening
LOOSENING-CHECK 0a6341f93c36: not a loosening
LOOSENING-CHECK daafe72c8732: not a loosening
LOOSENING-CHECK 506c291d7729: not a loosening
LOOSENING-CHECK 1c9782cc10fb: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK fd4765c7db20: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK 5811e05e54f6: finding: code changes without an entry or waiver now pass
LOOSENING-CHECK ef59c7f7334a: not a loosening
LOOSENING-CHECK 2a3b46757c65: not a loosening
LOOSENING-CHECK c9999fa4c4d6: not a loosening
LOOSENING-CHECK ccec3c4a6e33: not a loosening
LOOSENING-CHECK 6b1a2c4a41d6: not a loosening
LOOSENING-CHECK d06d9139dcb4: not a loosening
LOOSENING-CHECK a56d8f314616: not a loosening
LOOSENING-CHECK 45f675e1d3a8: not a loosening
LOOSENING-CHECK 006f67d74007: not a loosening
LOOSENING-CHECK 0f1a98358a76: not a loosening
LOOSENING-CHECK dbb1372e1786: not a loosening
LOOSENING-CHECK 319801499077: not a loosening
LOOSENING-CHECK 3eecfd841a0c: not a loosening
LOOSENING-CHECK 654d9f957f83: not a loosening
VERDICT: CONVERGED
