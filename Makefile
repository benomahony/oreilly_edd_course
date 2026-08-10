# ── O'Reilly EDD Course ───────────────────────────────────────────────────────
# Minimal Makefile: local model server, workshop steps, AI-native observability.
# Switch LLM providers with PROVIDER=lmstudio|google|openai (see providers.py).

LMS      := $(HOME)/.lmstudio/bin/lms
MODEL    := meta/muse-glimmer
WORKSHOP := src/oreilly_edd_course/workshop
OBS_UI   := http://localhost:6006

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

# ── Setup & inference ─────────────────────────────────────────────────────────

.PHONY: setup
setup: ## Install deps, start the model server, and load the model
	uv sync
	$(LMS) server start
	$(LMS) load "$(MODEL)"

.PHONY: status
status: ## Show model server status
	$(LMS) server status
	@echo
	$(LMS) ps

.PHONY: stop
stop: ## Stop the model server
	$(LMS) server stop

.PHONY: infer
infer: ## Smoke-test inference (PROVIDER=google to switch provider)
	uv run src/oreilly_edd_course/inference.py

# ── Workshop steps ────────────────────────────────────────────────────────────

.PHONY: step1 step2 step3 step4
step1: ## Run Step 1 (structured extraction & evals)
	uv run $(WORKSHOP)/step1_evals.py
step2: ## Run Step 2 (self-improving agent)
	uv run $(WORKSHOP)/step2_improver.py
step3: ## Run Step 3 (CI pipeline evals)
	uv run $(WORKSHOP)/step3_ci_pipeline.py
step4: ## Run Step 4 (production evals / monitoring)
	uv run $(WORKSHOP)/step4_production.py

.PHONY: step1-solution step2-solution step3-solution step4-solution
step1-solution: ## Run Step 1 solution
	uv run $(WORKSHOP)/step1_evals_solution.py
step2-solution: ## Run Step 2 solution
	uv run $(WORKSHOP)/step2_improver_solution.py
step3-solution: ## Run Step 3 solution
	uv run $(WORKSHOP)/step3_ci_pipeline_solution.py
step4-solution: ## Run Step 4 solution
	uv run $(WORKSHOP)/step4_production_solution.py

# ── Observability ─────────────────────────────────────────────────────────────

.PHONY: run
run: ## One-shot demo: start Phoenix, run traced inference, open the UI
	docker compose up -d
	uv run src/oreilly_edd_course/observability.py
	open "$(OBS_UI)"

.PHONY: obs-down
obs-down: ## Stop the observability stack
	docker compose down