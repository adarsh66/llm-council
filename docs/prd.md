# PRD: AI Expert Council

## 1. Product overview

### 1.1 Document title and version
- PRD: AI Expert Council
- Version: 1.1

### 1.2 Product summary
AI Expert Council is a web application that routes a user’s query to multiple LLMs, runs a peer review and ranking process, and synthesizes a final answer. It provides conversation management and a transparent, multi-model collaboration workflow. This PRD expands the system to support multiple collaboration modes, role assignment per mode, UI toggling between modes, and conversation deletion.

References:
- Backend orchestration: [`backend.council.stage1_collect_responses`](backend/council.py), [`backend.council.stage2_collect_rankings`](backend/council.py), [`backend.council.stage3_synthesize_final`](backend/council.py), [`backend.council.calculate_aggregate_rankings`](backend/council.py)
- Backend API: [backend/main.py](backend/main.py)
- Storage: [`backend.storage.list_conversations`](backend/storage.py), [`backend.storage.create_conversation`](backend/storage.py), [`backend.storage.get_conversation`](backend/storage.py), [`backend.storage.save_conversation`](backend/storage.py), [`backend.storage.add_user_message`](backend/storage.py), [`backend.storage.add_assistant_message`](backend/storage.py), [`backend.storage.update_conversation_title`](backend/storage.py)
- Azure inference: [`backend.azure_inference.query_models_parallel`](backend/azure_inference.py), [`backend.azure_inference.query_model`](backend/azure_inference.py)
- Frontend: [frontend/src/App.jsx](frontend/src/App.jsx), [frontend/src/api.js](frontend/src/api.js), [frontend/src/components/ChatInterface.jsx](frontend/src/components/ChatInterface.jsx), [frontend/src/components/Stage1.jsx](frontend/src/components/Stage1.jsx), [frontend/src/components/Stage2.jsx](frontend/src/components/Stage2.jsx), [frontend/src/components/Stage3.jsx](frontend/src/components/Stage3.jsx), [frontend/src/components/Sidebar.jsx](frontend/src/components/Sidebar.jsx)

## 2. Goals

### 2.1 Business goals
- Increase utility by supporting multiple collaboration strategies for varied tasks.
- Improve user control via role assignment per model and mode.
- Enhance retention through conversation management (deletion).
- Prepare for enterprise deployment on Azure App Service with durable storage.

### 2.2 User goals
- Choose the best collaboration style for a task (council, DxO, sequential, ensemble).
- Assign specific roles to individual models per mode.
- Toggle mode easily in UI before sending a message.
- Manage history by deleting conversations.

### 2.3 Non-goals
- Building proprietary LLMs.
- Complex team multi-user real-time collaboration (future work).
- Advanced analytics dashboards.

## 3. User personas

### 3.1 Key user types
- Technical user (developer, data scientist) needing rigorous multi-model answers.
- Product/PM user seeking consensus or decision orchestration.
- Researcher comparing model behaviors across modes.

### 3.2 Basic persona details
- Technical user: expert, daily usage, values transparency and control.
- PM user: intermediate, weekly usage, values decision frameworks.

### 3.3 Role-based access
- Single-user app initially; Admin role for deployment/ops is out-of-scope.

## 4. Functional requirements

- Conversation deletion (Priority: High)
  - Add ability to delete past conversations from the list.
  - Backend endpoint: DELETE /api/conversations/{id} (to be added in [backend/main.py](backend/main.py))
  - Storage deletion function to remove JSON file (new helper in [backend/storage.py](backend/storage.py))
  - UI: delete action in [frontend/src/components/Sidebar.jsx](frontend/src/components/Sidebar.jsx), confirmation dialog.

- Collaboration modes (Priority: High)
  - Support four modes:
    1) Council (current): parallel collection, peer rankings, chairman synthesis.
    2) DxO Decision Orchestrator: a decision framework where models play roles (e.g., Criteria Designer, Evaluator, Risk Assessor), produce scored alternatives, and orchestrate a decision outcome.
    3) Sequential (Chinese whispers) iterative improvement: pass the evolving answer through models in sequence with iteration count and convergence condition.
    4) Ensemble: run models independently and combine via weighted voting or confidence, optionally learned or user-defined weights.
  - Each mode defines execution topology and data flow.

- UI mode toggle (Priority: High)
  - Ability to select collaboration mode per conversation prior to sending messages.
  - Toggle control visible in [frontend/src/components/ChatInterface.jsx](frontend/src/components/ChatInterface.jsx) or header of conversation in [frontend/src/App.jsx](frontend/src/App.jsx).
  - Persist selected mode in conversation metadata via backend ([backend/main.py](backend/main.py), [`backend.storage.save_conversation`](backend/storage.py)).

- Role assignment per model per mode (Priority: High)
  - Users define roles for each candidate model per selected mode.
  - Roles differ by mode (examples):
    - Council: Analyst, Critic, Summarizer.
    - DxO: Criteria Designer, Option Generator, Evaluator, Risk Assessor, Decision Synthesizer.
    - Sequential: Improver at step k (with specific responsibilities).
    - Ensemble: Specialist domains (e.g., coding, math, reasoning), plus Combiner role.
  - UI: role configuration panel.
  - Backend: include role map in orchestration prompts and execution, stored per conversation.

## 5. User experience

### 5.1 Entry points & first-time user flow
- Landing, create conversation, select collaboration mode, assign roles (optional), send message, view staged outputs.

### 5.2 Core experience
- Conversation list in [frontend/src/components/Sidebar.jsx](frontend/src/components/Sidebar.jsx): create/select/delete conversations.
- Composer in [frontend/src/components/ChatInterface.jsx](frontend/src/components/ChatInterface.jsx): mode selector, roles config, message input.
- Staged results: Stage 1/2/3 components already exist; add variant views per mode.

### 5.3 Advanced features & edge cases
- Mode-specific parameters (e.g., iteration count for sequential; weights for ensemble).
- Persist settings per conversation; default sensible presets.
- Confirm destructive actions (delete).
- Handle failed model calls gracefully via existing streaming and error banners in [frontend/src/components/ChatInterface.jsx](frontend/src/components/ChatInterface.jsx).

### 5.4 UI/UX highlights
- Clear mode toggle and description tooltips.
- Role assignment UX with model badges from [`backend.config.COUNCIL_MODELS`](backend/config.py).
- Progress indicators per stage (already implemented in [frontend/src/App.jsx](frontend/src/App.jsx)) adapted for each mode.

## 6. Narrative
Users start a new conversation, select a collaboration mode, optionally assign roles to each model, and submit a query. The system orchestrates model interactions according to the mode, streams progress, and displays structured outputs. Users can remove conversations they no longer need.

## 7. Success metrics

### 7.1 User-centric metrics
- ≥80% of sessions use a non-default mode at least once.
- ≥90% success rate of conversation deletion actions.
- ≥75% user satisfaction (survey) with role assignment usefulness.

### 7.2 Business metrics
- Increased weekly active users by 25%.
- Reduced abandonment rate of first session by 20%.

### 7.3 Technical metrics
- 99% successful orchestration runs per request.
- P95 backend response (Stage 1 completion) ≤ 8s for 4 models.
- No orphaned JSON files after deletion.

## 8. Technical considerations

### 8.1 Integration points
- Backend orchestration expands beyond council using [`backend.azure_inference.query_models_parallel`](backend/azure_inference.py) and [`backend.azure_inference.query_model`](backend/azure_inference.py).
- Mode routing and prompts integrate into [`backend.council`](backend/council.py) or a new `backend/modes/*.py` structure.
- API client in [frontend/src/api.js](frontend/src/api.js) adds endpoints for deletion and mode/roles updates.

### 8.2 Data storage & privacy
- JSON files under DATA_DIR from [`backend.config.DATA_DIR`](backend/config.py).
- Delete must remove file and any cached references; ensure idempotency in [`backend.storage`](backend/storage.py).
- Avoid storing secrets in conversation payloads.

### 8.3 Scalability & performance
- Parallel calls for council/ensemble; sequential mode runs chained with streaming updates via SSE in [backend/main.py](backend/main.py).
- Consider Azure Files for durable storage; infra defined in [infra/main.bicep](infra/main.bicep); deployment script [scripts/deploy_appservice.sh](scripts/deploy_appservice.sh).

### 8.4 Potential challenges
- Role design consistency across modes.
- UI complexity for role assignment.
- Streaming updates for sequential steps.

## 9. Milestones & sequencing

### 9.1 Project estimate
- Size: M

### 9.2 Team size & composition
- Team size: 2-3 (Full-stack, Backend, Frontend)

### 9.3 Suggested phases
- Phase 1: Conversation deletion (1-2 days)
- Phase 2: Mode framework + UI toggle (3-4 days)
- Phase 3: Role assignment UX + backend integration (3-4 days)
- Phase 4: Implement DxO, Sequential, Ensemble orchestration (5-7 days)
- Phase 5: Validation, docs, polish (2-3 days)

## 10. User stories

### 10.1 Conversation deletion
- ID: GH-001
- Description: As a user, I want to delete past conversations so I can keep my workspace clean.
- Acceptance criteria:
  - [ ] Delete control is visible per conversation item in [frontend/src/components/Sidebar.jsx](frontend/src/components/Sidebar.jsx).
  - [ ] Clicking delete opens a confirmation dialog; cancel leaves data intact.
  - [ ] Confirming delete calls DELETE /api/conversations/{id}; backend removes JSON file via storage helper and returns 204.
  - [ ] List updates without the deleted item; no errors in logs.
  - [ ] Attempting to fetch a deleted conversation returns 404 in [frontend/src/api.js](frontend/src/api.js).

### 10.2 Collaboration mode toggle
- ID: GH-002
- Description: As a user, I want to select a collaboration mode before sending a message so the system orchestrates accordingly.
- Acceptance criteria:
  - [ ] Mode selector is available in composer UI in [frontend/src/components/ChatInterface.jsx](frontend/src/components/ChatInterface.jsx).
  - [ ] Selected mode is persisted in conversation metadata via backend ([backend/main.py](backend/main.py)).
  - [ ] Streaming events reflect the chosen mode steps in [frontend/src/App.jsx](frontend/src/App.jsx).
  - [ ] Default mode = Council; selection is remembered per conversation.

### 10.3 Role assignment per model per mode
- ID: GH-003
- Description: As a user, I want to assign roles to models for each collaboration mode to customize behavior.
- Acceptance criteria:
  - [ ] Role configuration panel lists models from [`backend.config.COUNCIL_MODELS`](backend/config.py).
  - [ ] Roles are mode-specific; UI prevents invalid role combinations.
  - [ ] Role map is saved with conversation metadata and used in orchestration prompts/execution.
  - [ ] Changing roles updates subsequent messages; prior messages retain original roles.

### 10.4 DxO Decision Orchestrator mode
- ID: GH-004
- Description: As a user, I want a decision orchestration mode where models generate criteria, options, evaluations, risks, and a synthesized decision.
- Acceptance criteria:
  - [ ] Distinct staged outputs for criteria, options, evaluations, risks, decision synthesis.
  - [ ] Roles (Designer, Generator, Evaluator, Risk Assessor, Synthesizer) respected per user configuration.
  - [ ] Final decision summary rendered in Stage 3 equivalent view.

### 10.5 Sequential (Chinese whispers) iterative improvement mode
- ID: GH-005
- Description: As a user, I want to run a sequential improvement chain through models with configurable iterations.
- Acceptance criteria:
  - [ ] Iteration steps stream individually with intermediate outputs.
  - [ ] Stop criteria (max iterations or convergence hint) is configurable.
  - [ ] Final improved output displayed at completion.

### 10.6 Ensemble mode
- ID: GH-006
- Description: As a user, I want to run all models independently and combine via ensemble strategies.
- Acceptance criteria:
  - [ ] Weighted voting or confidence-based merging implemented.
  - [ ] Weights configurable per model; stored with conversation metadata.
  - [ ] Final ensemble output rendered with attribution summary.

## Definition of done
- Code implemented and follows conventions.
- Unit tests ≥85% coverage for new modules.
- Integration tests cover mode routing and deletion.
- Documentation updated (README, inline comments).
- Validation of streaming UI for each mode.
- Deployment scripts and Bicep parameters updated if needed.

## Dependencies
- Existing council flow in [`backend.council`](backend/council.py) and SSE streaming in [backend/main.py](backend/main.py).
- Model configuration in [backend/config.py](backend/config.py).

## Open questions
- Exact role taxonomy per mode—finalize labels and constraints.
- Ensemble strategy defaults—simple majority vs. weighted by model type.

```// filepath: /home/ajanakiraman/build/llm-council/prd.md
# PRD: AI Expert Council

## 1. Product overview

### 1.1 Document title and version
- PRD: AI Expert Council
- Version: 1.1

### 1.2 Product summary
AI Expert Council is a web application that routes a user’s query to multiple LLMs, runs a peer review and ranking process, and synthesizes a final answer. It provides conversation management and a transparent, multi-model collaboration workflow. This PRD expands the system to support multiple collaboration modes, role assignment per mode, UI toggling between modes, and conversation deletion.

References:
- Backend orchestration: [`backend.council.stage1_collect_responses`](backend/council.py), [`backend.council.stage2_collect_rankings`](backend/council.py), [`backend.council.stage3_synthesize_final`](backend/council.py), [`backend.council.calculate_aggregate_rankings`](backend/council.py)
- Backend API: [backend/main.py](backend/main.py)
- Storage: [`backend.storage.list_conversations`](backend/storage.py), [`backend.storage.create_conversation`](backend/storage.py), [`backend.storage.get_conversation`](backend/storage.py), [`backend.storage.save_conversation`](backend/storage.py), [`backend.storage.add_user_message`](backend/storage.py), [`backend.storage.add_assistant_message`](backend/storage.py), [`backend.storage.update_conversation_title`](backend/storage.py)
- Azure inference: [`backend.azure_inference.query_models_parallel`](backend/azure_inference.py), [`backend.azure_inference.query_model`](backend/azure_inference.py)
- Frontend: [frontend/src/App.jsx](frontend/src/App.jsx), [frontend/src/api.js](frontend/src/api.js), [frontend/src/components/ChatInterface.jsx](frontend/src/components/ChatInterface.jsx), [frontend/src/components/Stage1.jsx](frontend/src/components/Stage1.jsx), [frontend/src/components/Stage2.jsx](frontend/src/components/Stage2.jsx), [frontend/src/components/Stage3.jsx](frontend/src/components/Stage3.jsx), [frontend/src/components/Sidebar.jsx](frontend/src/components/Sidebar.jsx)

## 2. Goals

### 2.1 Business goals
- Increase utility by supporting multiple collaboration strategies for varied tasks.
- Improve user control via role assignment per model and mode.
- Enhance retention through conversation management (deletion).
- Prepare for enterprise deployment on Azure App Service with durable storage.

### 2.2 User goals
- Choose the best collaboration style for a task (council, DxO, sequential, ensemble).
- Assign specific roles to individual models per mode.
- Toggle mode easily in UI before sending a message.
- Manage history by deleting conversations.

### 2.3 Non-goals
- Building proprietary LLMs.
- Complex team multi-user real-time collaboration (future work).
- Advanced analytics dashboards.

## 3. User personas

### 3.1 Key user types
- Technical user (developer, data scientist) needing rigorous multi-model answers.
- Product/PM user seeking consensus or decision orchestration.
- Researcher comparing model behaviors across modes.

### 3.2 Basic persona details
- Technical user: expert, daily usage, values transparency and control.
- PM user: intermediate, weekly usage, values decision frameworks.

### 3.3 Role-based access
- Single-user app initially; Admin role for deployment/ops is out-of-scope.

## 4. Functional requirements

- Conversation deletion (Priority: High)
  - Add ability to delete past conversations from the list.
  - Backend endpoint: DELETE /api/conversations/{id} (to be added in [backend/main.py](backend/main.py))
  - Storage deletion function to remove JSON file (new helper in [backend/storage.py](backend/storage.py))
  - UI: delete action in [frontend/src/components/Sidebar.jsx](frontend/src/components/Sidebar.jsx), confirmation dialog.

- Collaboration modes (Priority: High)
  - Support four modes:
    1) Council (current): parallel collection, peer rankings, chairman synthesis.
    2) DxO Decision Orchestrator: a decision framework where models play roles (e.g., Criteria Designer, Evaluator, Risk Assessor), produce scored alternatives, and orchestrate a decision outcome.
    3) Sequential (Chinese whispers) iterative improvement: pass the evolving answer through models in sequence with iteration count and convergence condition.
    4) Ensemble: run models independently and combine via weighted voting or confidence, optionally learned or user-defined weights.
  - Each mode defines execution topology and data flow.

- UI mode toggle (Priority: High)
  - Ability to select collaboration mode per conversation prior to sending messages.
  - Toggle control visible in [frontend/src/components/ChatInterface.jsx](frontend/src/components/ChatInterface.jsx) or header of conversation in [frontend/src/App.jsx](frontend/src/App.jsx).
  - Persist selected mode in conversation metadata via backend ([backend/main.py](backend/main.py), [`backend.storage.save_conversation`](backend/storage.py)).

- Role assignment per model per mode (Priority: High)
  - Users define roles for each candidate model per selected mode.
  - Roles differ by mode (examples):
    - Council: Analyst, Critic, Summarizer.
    - DxO: Criteria Designer, Option Generator, Evaluator, Risk Assessor, Decision Synthesizer.
    - Sequential: Improver at step k (with specific responsibilities).
    - Ensemble: Specialist domains (e.g., coding, math, reasoning), plus Combiner role.
  - UI: role configuration panel.
  - Backend: include role map in orchestration prompts and execution, stored per conversation.

## 5. User experience

### 5.1 Entry points & first-time user flow
- Landing, create conversation, select collaboration mode, assign roles (optional), send message, view staged outputs.

### 5.2 Core experience
- Conversation list in [frontend/src/components/Sidebar.jsx](frontend/src/components/Sidebar.jsx): create/select/delete conversations.
- Composer in [frontend/src/components/ChatInterface.jsx](frontend/src/components/ChatInterface.jsx): mode selector, roles config, message input.
- Staged results: Stage 1/2/3 components already exist; add variant views per mode.

### 5.3 Advanced features & edge cases
- Mode-specific parameters (e.g., iteration count for sequential; weights for ensemble).
- Persist settings per conversation; default sensible presets.
- Confirm destructive actions (delete).
- Handle failed model calls gracefully via existing streaming and error banners in [frontend/src/components/ChatInterface.jsx](frontend/src/components/ChatInterface.jsx).

### 5.4 UI/UX highlights
- Clear mode toggle and description tooltips.
- Role assignment UX with model badges from [`backend.config.COUNCIL_MODELS`](backend/config.py).
- Progress indicators per stage (already implemented in [frontend/src/App.jsx](frontend/src/App.jsx)) adapted for each mode.

## 6. Narrative
Users start a new conversation, select a collaboration mode, optionally assign roles to each model, and submit a query. The system orchestrates model interactions according to the mode, streams progress, and displays structured outputs. Users can remove conversations they no longer need.

## 7. Success metrics

### 7.1 User-centric metrics
- ≥80% of sessions use a non-default mode at least once.
- ≥90% success rate of conversation deletion actions.
- ≥75% user satisfaction (survey) with role assignment usefulness.

### 7.2 Business metrics
- Increased weekly active users by 25%.
- Reduced abandonment rate of first session by 20%.

### 7.3 Technical metrics
- 99% successful orchestration runs per request.
- P95 backend response (Stage 1 completion) ≤ 8s for 4 models.
- No orphaned JSON files after deletion.

## 8. Technical considerations

### 8.1 Integration points
- Backend orchestration expands beyond council using [`backend.azure_inference.query_models_parallel`](backend/azure_inference.py) and [`backend.azure_inference.query_model`](backend/azure_inference.py).
- Mode routing and prompts integrate into [`backend.council`](backend/council.py) or a new `backend/modes/*.py` structure.
- API client in [frontend/src/api.js](frontend/src/api.js) adds endpoints for deletion and mode/roles updates.

### 8.2 Data storage & privacy
- JSON files under DATA_DIR from [`backend.config.DATA_DIR`](backend/config.py).
- Delete must remove file and any cached references; ensure idempotency in [`backend.storage`](backend/storage.py).
- Avoid storing secrets in conversation payloads.

### 8.3 Scalability & performance
- Parallel calls for council/ensemble; sequential mode runs chained with streaming updates via SSE in [backend/main.py](backend/main.py).
- Consider Azure Files for durable storage; infra defined in [infra/main.bicep](infra/main.bicep); deployment script [scripts/deploy_appservice.sh](scripts/deploy_appservice.sh).

### 8.4 Potential challenges
- Role design consistency across modes.
- UI complexity for role assignment.
- Streaming updates for sequential steps.

## 9. Milestones & sequencing

### 9.1 Project estimate
- Size: M

### 9.2 Team size & composition
- Team size: 2-3 (Full-stack, Backend, Frontend)

### 9.3 Suggested phases
- Phase 1: Conversation deletion (1-2 days)
- Phase 2: Mode framework + UI toggle (3-4 days)
- Phase 3: Role assignment UX + backend integration (3-4 days)
- Phase 4: Implement DxO, Sequential, Ensemble orchestration (5-7 days)
- Phase 5: Validation, docs, polish (2-3 days)

## 10. User stories

### 10.1 Conversation deletion
- ID: GH-001
- Description: As a user, I want to delete past conversations so I can keep my workspace clean.
- Acceptance criteria:
  - [ ] Delete control is visible per conversation item in [frontend/src/components/Sidebar.jsx](frontend/src/components/Sidebar.jsx).
  - [ ] Clicking delete opens a confirmation dialog; cancel leaves data intact.
  - [ ] Confirming delete calls DELETE /api/conversations/{id}; backend removes JSON file via storage helper and returns 204.
  - [ ] List updates without the deleted item; no errors in logs.
  - [ ] Attempting to fetch a deleted conversation returns 404 in [frontend/src/api.js](frontend/src/api.js).

### 10.2 Collaboration mode toggle
- ID: GH-002
- Description: As a user, I want to select a collaboration mode before sending a message so the system orchestrates accordingly.
- Acceptance criteria:
  - [ ] Mode selector is available in composer UI in [frontend/src/components/ChatInterface.jsx](frontend/src/components/ChatInterface.jsx).
  - [ ] Selected mode is persisted in conversation metadata via backend ([backend/main.py](backend/main.py)).
  - [ ] Streaming events reflect the chosen mode steps in [frontend/src/App.jsx](frontend/src/App.jsx).
  - [ ] Default mode = Council; selection is remembered per conversation.

### 10.3 Role assignment per model per mode
- ID: GH-003
- Description: As a user, I want to assign roles to models for each collaboration mode to customize behavior.
- Acceptance criteria:
  - [ ] Role configuration panel lists models from [`backend.config.COUNCIL_MODELS`](backend/config.py).
  - [ ] Roles are mode-specific; UI prevents invalid role combinations.
  - [ ] Role map is saved with conversation metadata and used in orchestration prompts/execution.
  - [ ] Changing roles updates subsequent messages; prior messages retain original roles.

### 10.4 DxO Decision Orchestrator mode
- ID: GH-004
- Description: As a user, I want a decision orchestration mode where models generate criteria, options, evaluations, risks, and a synthesized decision.
- Acceptance criteria:
  - [ ] Distinct staged outputs for criteria, options, evaluations, risks, decision synthesis.
  - [ ] Roles (Designer, Generator, Evaluator, Risk Assessor, Synthesizer) respected per user configuration.
  - [ ] Final decision summary rendered in Stage 3 equivalent view.

### 10.5 Sequential (Chinese whispers) iterative improvement mode
- ID: GH-005
- Description: As a user, I want to run a sequential improvement chain through models with configurable iterations.
- Acceptance criteria:
  - [ ] Iteration steps stream individually with intermediate outputs.
  - [ ] Stop criteria (max iterations or convergence hint) is configurable.
  - [ ] Final improved output displayed at completion.

### 10.6 Ensemble mode
- ID: GH-006
- Description: As a user, I want to run all models independently and combine via ensemble strategies.
- Acceptance criteria:
  - [ ] Weighted voting or confidence-based merging implemented.
  - [ ] Weights configurable per model; stored with conversation metadata.
  - [ ] Final ensemble output rendered with attribution summary.

## Definition of done
- Code implemented and follows conventions.
- Unit tests ≥85% coverage for new modules.
- Integration tests cover mode routing and deletion.
- Documentation updated (README, inline comments).
- Validation of streaming UI for each mode.
- Deployment scripts and Bicep parameters updated if needed.

## Dependencies
- Existing council flow in [`backend.council`](backend/council.py) and SSE streaming in [backend/main.py](backend/main.py).
- Model configuration in [backend/config.py](backend/config.py).

## Open questions
- Exact role taxonomy per mode—finalize labels and constraints.
- Ensemble strategy defaults—simple majority vs. weighted by model type.
