# Phase 6 freeze record

Frozen on 2026-11-21, **before any test-split prompt was read, printed or sent anywhere.**
Parent commit (code state being frozen): `4f26f611c6f56addc745bae4d1343ebe2f6b753e`. The freeze commit adds only this file and is tagged `phase6-frozen` (local tag, not pushed).

## Bug rule (docs/PHASE6_PLAN.md section 1)

Only a crash or a wiring bug (not a "this answer was graded wrong" preference) may be fixed after the test split is opened.
Every fix is logged in the table below with its reason, and **all** systems are re-run after it, never only the affected tasks.
Policy, thresholds, prompts, classifiers, graders and the judge rubric cannot change.

## SHA-256 of frozen files

| File | SHA-256 |
|---|---|
| `eval/results/phase4/routing_policy.json` | `14c61b8d2746227a8bb470a1f05ffa79574a476e697c275905057695cd432b82` |
| `eval/results/phase4/routing_policy_gpu_server.json` | `c5ed77a7218ab0968015c341ac6d6d3228388437bf41d66ec6a6b91e1366d369` |
| `router/artifacts/task_type_lr.npz` | `7380d85d0400df90e491d5607bf09e0637c30454494640638a3d36e53f6c2e49` |
| `router/artifacts/difficulty_lr.npz` | `78ccf66c04f65bec80bb3ac3d3b37c5de0088a91ef218300c6daa41a85040978` |
| `eval/tasks_8cat.json` | `402faad1c3e12d98de8118c753470dd90e94ceb116e03253c115e2a02b8ece8d` |
| `eval/model_prices.json` | `880b36de8b499b4926c75be9c67244916cdf0f4d37946658689f01b0ec377340` |
| `eval/graders/__init__.py` | `5f5d97720d915869d72551343898af7c1d7712ed4ddf2a975d043563dcbafe0a` |
| `eval/graders/code_tests.py` | `cd87c38e0c987b26f5214d24258acbe798e1d0ab8edc37d612ecbbda8e942a5e` |
| `eval/graders/common.py` | `b927a511e3bdbecd07d60ec40a653a1f972b00e55e558076bae36c14873adb5f` |
| `eval/graders/constraint.py` | `84dcce114983755bdc62560d6624e2d3214e4d735140163a71b58829a2a742c1` |
| `eval/graders/exact.py` | `f660388579670168ecd01d8f0ea0f653d26b3661d4ac731b793d7b40fe77eb6f` |
| `eval/graders/formats.py` | `af5c92d8c13a780548c3b3b29a577ee72292c2d478e3d76009959d5710acd1c5` |
| `eval/graders/judge.py` | `d354d8d3151208ed84ba351de9d69e2152e3c738f9d608622681fd527d95cd1e` |
| `eval/graders/label.py` | `52039e254da681ee5bbbc4ef50ccd73db4f681c2616c159406de5925e233cd06` |
| `eval/graders/language.py` | `0f3dcb171fb25d7003ea565a41d1d507563c2ed8c5629ece332af56e22bf5382` |
| `eval/graders/ner_f1.py` | `b33779652649d01c6784c13ab3e8bdcad7cff97f1bc41b4a183de4c712146770` |
| `eval/graders/numeric.py` | `94253e2c2abc74930305c2b61a907cdd990ad7a3232848c944bd1741c8f58de1` |
| `eval/graders/test_graders.py` | `b2e249811b7255873969ea91e103e7b352dcbb265472142366f9abb15b1445d5` |
| `eval/graders/test_language.py` | `4ef17f47c34a0c83115fe91b765c104517a7f2a34f4fccd087350c8e23aa0008` |
| `router/__init__.py` | `2c31b014ec0f58921a01d9c9114199060b02de5c86e8bd5e866a3dca0a650d9e` |
| `router/classify.py` | `f50f43ff0c232d066be19c4737aaf6068b072dc6bf2cecb9807bfef31de67e3f` |
| `router/config.py` | `f52126c71ca8e88c1e108c61749da7204b15db8d168f4dbdc8fa205b11240a6e` |
| `router/data.py` | `d8f5dbcc0340578bb3de438c856f792f6561bf657b25caf8c5a052444db81088` |
| `router/difficulty.py` | `f1d1985c3bde86bcb23e48c3e1dea951ded9c79c91f7a847a34790b4f7e2d795` |
| `router/embed_fast.py` | `f2b8c20453eb9849506c9bb62e21deeee3d20e0923168772993c04f29b9f874d` |
| `router/embeddings.py` | `2003c73c8f33dd945ad420e51582be13124b97eecb768c7b09b29aafdf839dc9` |
| `router/fakes.py` | `cdd516dcc6befe7b375b35dafb5d75f7840e60dd10c53238a3e606eb43c6d23a` |
| `router/labeler.py` | `374e6aae41ccd5db167e9ae7b4c728c75738b09682f29fcb0137278f4f702a15` |
| `router/logging.py` | `3e9d381509577e066c50c1c7d815759f24101ff4cbf8a8638238536c0f358306` |
| `router/models.py` | `cde5878dfca72068823d86cebcc8d8cdfe39a82027475b197fcfbcc84f78ac5d` |
| `router/pipeline.py` | `6b941e252c4768b131a19177e69fd806812a5499666ee5f8bbd8f49f40ba5185` |
| `router/policy.py` | `fcb00596b270bfc1760ead95f84ef78a79afaeee67f9a234531cd1c46ac6eec2` |
| `router/recorded.py` | `1aa5f796b9d5e3224323c71b85b11cf1fc596e083b5569a5e9bb42e0a808a8d3` |
| `router/replay_check.py` | `960f7852913632bbe7a0b4040f1c72cbd38cd07eedb2525d143aefa18b11c489` |
| `router/run.py` | `3a7e56c6eddab8d72e3951a3430e23cd4a049873e4e36dbd883dd1badc82e79a` |
| `router/solvers/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `router/solvers/logic_solver.py` | `afad99b518b70feed971a5947606ebb7d806f4e5b6500eb64ca798b7a94f74dc` |
| `router/solvers/math_solver.py` | `92a87cb660ae146455099fbbe2ab6b9d1740c0143565e9b5d15e3ffa756d1c95` |
| `router/solvers/safe_arith.py` | `6a9eedb0fdd8c55bc04cc47f04e38b28eab9b6db38fae07d3965e9c476ea4785` |
| `router/solvers/translate.py` | `934204cc11d99c90f0560a197017bd389cc48b374a67b10dc576c8e65715dde2` |
| `router/tests/conftest.py` | `073c7de517c419e73a956bee5390adc5d0dee87efdbaf35f4563a629b70349c2` |
| `router/tests/test_classify.py` | `f1c1498a4afc9da5bc0f6d9f314212c467a58f0f3ec0a9794658318aa1b01004` |
| `router/tests/test_embed_fast.py` | `49bd6c53001f905c7c46b702f14fcf1059b1ded6f5eab96ad20049121db7f0ed` |
| `router/tests/test_eval_translators.py` | `e25edceb9bb5e498f615c77fbc229e569cc38b16504a0d6acf85266ced5e7a0a` |
| `router/tests/test_phase5_models_policy.py` | `76225daa3edacfaa989b1939d039e31f847cc5dc5fe6c0653423c95dd31c4ced` |
| `router/tests/test_pipeline.py` | `d27e0f318d9f0700e7e054ecf669a6e0d5da33d979889bda27f7278890433a93` |
| `router/tests/test_policy.py` | `7b2986d381cdf2a474ea0328de2cd63074c4b44c05ab0a7ddd545a2affe557fe` |
| `router/tests/test_replay_consistency.py` | `bf6c6a63a2eb20bdb673c70cd0a75817e6a3670ea799bb73d121708384485957` |
| `router/tests/test_run.py` | `d6077c7203266806b12b584cc2109f26de53b66a6b4de3429f70aafdf139b515` |
| `router/tests/test_solvers.py` | `ca192ec63e16d66a28933954608a450a76cb4b70f9946829ce487bd9e8e3bc59` |
| `router/tests/test_translate.py` | `e695ba8d643c98b085fb11e823883db9944997447f7ae92206c9a9c276898b02` |
| `router/tests/test_validators.py` | `2934d6d47c0e611fe74d8d15948a9c9376691144b3ac7487774cec7c9574e6eb` |
| `router/validators.py` | `8c252b9511a4d1e3fdbaef43080f1ed7ab8622a223268e5c7e2166582054b7d6` |

Router source = every `.py` under `router/` (tests included), plus `router/artifacts/*.npz` (the classifier and difficulty models the router loads).

## Post-freeze fixes (crash / wiring bugs only)

| Date | File | Bug | Reason it is a crash/wiring bug | Systems re-run |
|---|---|---|---|---|
| (none) | | | | |
