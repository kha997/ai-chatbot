# Independent review of the Issue #63 public corpus

Verdict **PARTIAL_CORPUS_READY / BLOCKED_HELDOUT_CUSTODY** at technical SHA [d0f475f0](https://github.com/kha997/ai-chatbot/commit/d0f475f0ebcfa5d2cca6dc2437223bf6dbaa145d). Fresh-context Codex reviewer `/root/corpus63_review` inspected this exact commit and authored no code. This records independent review in a separate Codex context. Architecture Acceptance is pending.

The reviewer checked provenance and diversity across 9 products, 5 categories, 5 units and 37 claims in eight families. Twelve public development oracles remain distinct from the 60 reserved scored IDs. Zero exact held-out questions, oracles, private receipts or storage locators appear in the reviewed delta. No authorized private store was evidenced. Independence across actual private cases cannot be assessed until those cases exist.

During review the negative reason pattern rejected the existing underscore-form oracle reasons. The revised pattern retained the actual oracles and added a regression test. A second regression showed a valid amount failing when the caller narrowed its Decimal exponent range. A dedicated Decimal context fixed that failure. Documentation and the function contract now require callers to validate quote slots before using the amount-only helper. The reviewer rechecked these corrections at the final technical SHA and found no outstanding blocker to accepting the public package.

- Offline stdlib validator and 15 new tests PASS on Windows and isolated WSL. WSL namespace had only loopback down and no default routes. Commands: `python3 -B -m scripts.offline_corpus63` and `python3 -B -m unittest discover -s tests -p "test_offline_corpus63.py"`.
- Independent review validated both schemas and all four public instances with the existing WSL Draft 2020-12 validator. Independently checked canonical byte lengths and all five manifest hashes. Manifest SHA-256 `8f588ecd8251a874effccc4f23c67852aaeafed6bfcf2e6fe5c57edacd516e12`.
- Existing 73 quote tests PASS. `git diff --check` PASS. Hosted CI at the technical SHA: [offline corpus](https://github.com/kha997/ai-chatbot/actions/runs/45213683833) and [quote acceptance](https://github.com/kha997/ai-chatbot/actions/runs/45213683860).
- AI, actual held-out scoring, and all six business E2Es remain NOT_RUN. No provider, upload, private custody or spending occurred.

The final status and receipt commit changes prose only. The exact PR HEAD and hosted CI are recorded on [PR #65](https://github.com/kha997/ai-chatbot/pull/65).
