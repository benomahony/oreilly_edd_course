# ── O'Reilly EDD Course ───────────────────────────────────────────────────────
# Make targets for LM Studio setup, inference, and local observability.

LMS        := $(HOME)/.lmstudio/bin/lms
MODEL      := qwen/qwen3.6-35b-a3b 
OBS_UI     := http://localhost:16686
WORKSHOP   := src/oreilly_edd_course/workshop

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ── Setup ─────────────────────────────────────────────────────────────────────

.PHONY: setup
setup: uv-sync lmstudio-setup ## Install deps and bring up LM Studio

.PHONY: uv-sync
uv-sync: ## Install Python dependencies
	uv sync

# ── LM Studio ─────────────────────────────────────────────────────────────────

.PHONY: lmstudio-setup
lmstudio-setup: lmstudio-download lmstudio-start lmstudio-load ## Download model, start server, load model

.PHONY: lmstudio-download
lmstudio-download: ## Download the course model (idempotent)
	$(LMS) get "$(MODEL)"

.PHONY: lmstudio-start
lmstudio-start: ## Start the local inference server
	$(LMS) server start

.PHONY: lmstudio-stop
lmstudio-stop: ## Stop the local inference server
	$(LMS) server stop

.PHONY: lmstudio-status
lmstudio-status: ## Show server status and loaded models
	$(LMS) server status
	@echo
	$(LMS) ps

.PHONY: lmstudio-load
lmstudio-load: ## Load the course model into memory
	$(LMS) load "$(MODEL)"

.PHONY: lmstudio-unload
lmstudio-unload: ## Unload the course model from memory
	$(LMS) unload "$(MODEL)"

# ── Inference ─────────────────────────────────────────────────────────────────

.PHONY: infer
infer: ## Smoke-test inference against the running model
	uv run src/oreilly_edd_course/inference.py

.PHONY: step1 step2 step3 step4
step1: ## Run Step 1 exercise (structured extraction & evals)
	uv run $(WORKSHOP)/step1_evals.py
step2: ## Run Step 2 exercise (self-improving agent)
	uv run $(WORKSHOP)/step2_improver.py
step3: ## Run Step 3 exercise (CI pipeline evals)
	uv run $(WORKSHOP)/step3_ci_pipeline.py
step4: ## Run Step 4 exercise (production evals / monitoring)
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

.PHONY: obs-up
obs-up: ## Start the local observability stack (Jaeger)
	docker compose up -d

.PHONY: obs-down
obs-down: ## Stop the local observability stack
	docker compose down

.PHONY: obs-logs
obs-logs: ## Tail observability stack logs
	docker compose logs -f

.PHONY: obs-ui
obs-ui: ## Open the Jaeger UI
	open "$(OBS_UI)"

.PHONY: obs-run
obs-run: ## Run a traced inference and send spans to Jaeger
	uv run src/oreilly_edd_course/observability.py
