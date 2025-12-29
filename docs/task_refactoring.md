# Refactoring Tasks (Issues #80, #81, #82)

- [ ] **Refactor `match_processor.py` (#81)**
    - [ ] Create `src/clients/api_football_client.py`
    - [ ] Create `src/domain/match_ranker.py`
    - [ ] Create `src/domain/match_selector.py`
    - [ ] Modify `src/match_processor.py` to utilize the new components
- [ ] **Refactor `cache_warmer.py` (#82)**
    - [ ] Create `src/utils/execution_policy.py`
    - [ ] Modify `src/cache_warmer.py` to utilize `ExecutionPolicy` and `ApiFootballClient`
- [ ] **Refactor `main.py` (#80)**
    - [ ] Create `src/workflows/generate_guide_workflow.py`
    - [ ] Modify `main.py` to use `GenerateGuideWorkflow`
- [ ] **Verification**
    - [ ] Mock mode verification
    - [ ] Debug mode verification
