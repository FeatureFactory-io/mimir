.DEFAULT_GOAL := help
PYTHON  := .venv/bin/python
PIP     := .venv/bin/pip
PYTEST  := .venv/bin/pytest
RUFF    := .venv/bin/ruff

##@ General

.PHONY: help
help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Provision

.PHONY: provision
provision: ## Python venv + deps, migrations, dark-factory CLI tools, verify
	python3 -m venv .venv
	$(PIP) install --upgrade pip -q
	$(PIP) install -r requirements.txt -q
	@cp -n .env.example .env 2>/dev/null && echo "Created .env from .env.example — fill in your values" || echo ".env already exists"
	$(PYTHON) manage.py migrate --noinput
	@bash scripts/provision-factory-deps.sh
	@bash scripts/check-factory-prereqs.sh
	@echo ""
	@echo "Provision complete."
	@echo "  App:  make run"
	@echo "  MCP:  make mcp"
	@echo "  Personal DB (once): make dev-db-init   # needs MIMIR_DB_PATH in .env"
	@echo "  Factory: scripts/preflight.sh '<milestone>' then scripts/factory.sh '<slug>'"

.PHONY: factory-check
factory-check: ## Re-verify all factory prereqs (includes gh auth + cursor-agent)
	@bash scripts/check-factory-prereqs.sh --strict

.PHONY: provision-factory
provision-factory: ## Alias: re-install factory CLI deps only (full setup: make provision)
	@bash scripts/provision-factory-deps.sh
	@bash scripts/check-factory-prereqs.sh

##@ Development

.PHONY: run
run: ## Start Django web server (port 8000)
	$(PYTHON) manage.py runserver 8000

.PHONY: mcp
mcp: ## Start MCP server for the default admin user
	$(PYTHON) manage.py mcp_server --user=admin

.PHONY: shell
shell: ## Open Django shell
	$(PYTHON) manage.py shell

.PHONY: migrate
migrate: ## Run pending migrations
	$(PYTHON) manage.py migrate --noinput

.PHONY: makemigrations
makemigrations: ## Generate new migrations
	$(PYTHON) manage.py makemigrations

.PHONY: createsuperuser
createsuperuser: ## Create a Django superuser
	$(PYTHON) manage.py createsuperuser

.PHONY: demo
demo: ## Load demo FeatureFactory data
	$(PYTHON) manage.py create_demo_fdd

##@ Testing
# Test settings only for test targets — do not export globally (breaks make run → mimir_test.db).

.PHONY: test
test: export DJANGO_SETTINGS_MODULE := mimir.settings.test
test: ## Run all tests (mirrors CI)
	$(PYTEST) tests/ \
	  --ignore=tests/e2e \
	  --ignore=tests/integration/test_mcp_server_acceptance.py \
	  --ignore=tests/integration/test_mcp_facade.py \
	  --ignore=tests/integration/test_mcp_e2e_all_tools.py \
	  --ignore=tests/unit/test_activity_graph_service.py

.PHONY: test-unit
test-unit: export DJANGO_SETTINGS_MODULE := mimir.settings.test
test-unit: ## Run unit tests only
	$(PYTEST) tests/unit/

.PHONY: test-factory
test-factory: export DJANGO_SETTINGS_MODULE := mimir.settings.test
test-factory: ## Run dark-factory contract tests + shell syntax checks
	@bash -n scripts/factory.sh scripts/preflight.sh scripts/claim.sh scripts/done.sh \
	         scripts/reject.sh scripts/status.sh scripts/bb-append.sh \
	         scripts/verify-result.sh scripts/integrate.sh scripts/release.sh \
	         scripts/archive.sh scripts/rescue-result.sh scripts/factory-git.sh \
	         scripts/lib/factory-common.sh scripts/lib/factory-git-inner.sh
	@bash tests/unit/test_promote_revision_guard.sh
	$(PYTEST) tests/unit/test_factory_preflight.py \
	          tests/unit/test_verify_result.py \
	          tests/unit/test_integrate_guards.py \
	          tests/unit/test_release_guards.py \
	          tests/unit/test_factory_status.py \
	          tests/unit/test_factory_claim_deps.py -v

.PHONY: test-integration
test-integration: export DJANGO_SETTINGS_MODULE := mimir.settings.test
test-integration: ## Run integration tests only
	$(PYTEST) tests/integration/ \
	  --ignore=tests/integration/test_mcp_server_acceptance.py \
	  --ignore=tests/integration/test_mcp_facade.py \
	  --ignore=tests/integration/test_mcp_e2e_all_tools.py

.PHONY: test-e2e
test-e2e: export DJANGO_SETTINGS_MODULE := mimir.settings.test
test-e2e: ## Run Playwright E2E tests (requires running server)
	$(PYTEST) tests/e2e/

.PHONY: test-at-harness test-at-experts
test-at-harness: ## Prove the Django-client acceptance harness on its real test DB
	DJANGO_SETTINGS_MODULE=mimir.settings.acceptance $(PYTHON) manage.py behave --simple --tags=@harness docs/features/act-0-auth/test-harness.feature

test-at-experts: ## Run implemented Experts living specifications, excluding WIP
	DJANGO_SETTINGS_MODULE=mimir.settings.acceptance $(PYTHON) manage.py behave --simple --tags='@experts and not @wip' docs/features/act-18-experts/ docs/features/act-0-auth/experts-navigation.feature

.PHONY: test-agent-experts
test-agent-experts: ## Required Experts agent proofs after BPE; missing/empty suite fails
	$(PYTEST) tests/integration/test_experts_summary_proofs.py -m agent_proof

##@ Code Quality

.PHONY: lint
lint: ## Run ruff linter + format check
	$(RUFF) check .
	$(RUFF) format --check .

.PHONY: format
format: ## Auto-format code with ruff
	$(RUFF) format .

.PHONY: lint-fix
lint-fix: ## Run ruff linter with auto-fix
	$(RUFF) check --fix .

##@ Database
# Committed seed: mimir.db. Personal sandbox: mimir.dev.db via MIMIR_DB_PATH in .env.
# Production on EB uses Postgres (DATABASE_URL env var).

.PHONY: dev-db-init
dev-db-init: ## [local] Copy seed mimir.db → mimir.dev.db (first-time personal sandbox)
	@if [ -f mimir.dev.db ]; then \
	  echo "mimir.dev.db already exists — use 'make refresh-dev-db' to reset from seed."; \
	  exit 1; \
	fi
	cp mimir.db mimir.dev.db
	@echo "Created mimir.dev.db from mimir.db."
	@echo "Set MIMIR_DB_PATH=mimir.dev.db in .env (see .env.example), then: make run"

.PHONY: refresh-dev-db
refresh-dev-db: ## [local] Overwrite mimir.dev.db from seed mimir.db and run migrations
	cp mimir.db mimir.dev.db
	$(PYTHON) manage.py migrate --noinput
	@echo "mimir.dev.db refreshed from committed seed (mimir.db)."

.PHONY: dev-db-reset
dev-db-reset: ## [local] Delete mimir.dev.db and recreate from seed mimir.db
	@echo "WARNING: This will delete mimir.dev.db and all personal local data."
	@read -p "Continue? [y/N] " ans && [ "$$ans" = "y" ]
	rm -f mimir.dev.db mimir.dev.db-shm mimir.dev.db-wal
	cp mimir.db mimir.dev.db
	$(PYTHON) manage.py migrate --noinput
	@echo "mimir.dev.db recreated from seed."

.PHONY: db-reset
db-reset: ## [local] Delete mimir.db and re-run migrations (destroys committed seed file — rare)
	@echo "WARNING: This will delete mimir.db and all data in the seed database."
	@read -p "Continue? [y/N] " ans && [ "$$ans" = "y" ]
	rm -f mimir.db mimir.db-shm mimir.db-wal
	$(PYTHON) manage.py migrate --noinput
	@echo "Database reset. Run 'make demo' to reload demo data."

.PHONY: backup
backup: ## [prod] pg_dump + dumpdata to S3 — requires S3_BACKUP_BUCKET and DATABASE_URL
	@bash scripts/pre-deploy-backup.sh

##@ Deploy (AWS EB)

# Release flow (mirrors Huginn):
#   gh release create vX.Y.Z
#     → CI: test → build → deploy-idle.sh (dynamically resolves idle env) → staging smoke
#   make swap   (after human review of idle URL)
#     → promote-prod.sh: resolves live/idle, revision guard (/health/ or VersionLabel), swap, smoke
#
# Two physical EB envs whose CNAMEs rotate on every swap:
#   mimir-prod  /  mimir-idle
# Route53 CNAME → mimir-prod.eba-… (stable label; follows the swap automatically).
EB_APP    ?= mimir
EB_ENV_A  ?= mimir-prod
EB_ENV_B  ?= mimir-idle
AWS_REGION ?= us-east-1

.PHONY: swap
swap: ## [prod] Promote idle → prod: resolve live/idle, SHA guard, CNAME swap, smoke prod
	@EB_APP=$(EB_APP) EB_ENV_A=$(EB_ENV_A) EB_ENV_B=$(EB_ENV_B) \
	  AWS_DEFAULT_REGION=$(AWS_REGION) bash scripts/promote-prod.sh

.PHONY: idle-start
idle-start: ## Start the idle EB env if scaled to 0 (used by deploy-idle.sh before backup)
	@EB_APP=$(EB_APP) EB_ENV_A=$(EB_ENV_A) EB_ENV_B=$(EB_ENV_B) \
	  AWS_DEFAULT_REGION=$(AWS_REGION) PROD_CNAME_SUBSTRING=mimir-prod.eba- EB_IDLE_WAIT_SSM=1 \
	  bash scripts/eb_idle_power.sh start

.PHONY: idle-stop
idle-stop: ## Scale the idle EB env to 0 instances — never touches the env holding mimir-prod CNAME
	@EB_APP=$(EB_APP) EB_ENV_A=$(EB_ENV_A) EB_ENV_B=$(EB_ENV_B) \
	  AWS_DEFAULT_REGION=$(AWS_REGION) PROD_CNAME_SUBSTRING=mimir-prod.eba- \
	  bash scripts/eb_idle_power.sh stop

.PHONY: eb-status
eb-status: ## Show health, CNAME, and version of both EB environments
	@aws elasticbeanstalk describe-environments \
	  --application-name $(EB_APP) \
	  --environment-names $(EB_ENV_A) $(EB_ENV_B) \
	  --query "Environments[*].{Env:EnvironmentName,Status:Status,Health:Health,Version:VersionLabel,CNAME:CNAME}" \
	  --output table --region $(AWS_REGION)

##@ Cleanup

.PHONY: clean
clean: ## Remove Python bytecode and pytest cache
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache htmlcov .coverage coverage.xml report.html

##@ Experts replay — planned gates (unimplemented until PIN-05 GO)

.PHONY: test-experts-s01-backend
test-experts-s01-backend:
	$(PYTHON) -m pytest tests/unit/test_experts_navigation.py::test_is_experts_path_with_local_paths_returns_expected_match tests/unit/test_experts_navigation.py::test_is_experts_path_with_invalid_input_raises_value_error tests/unit/test_experts_navigation.py::test_collaborate_items_with_experts_preserves_existing_links tests/unit/test_experts_navigation.py::test_primary_nav_section_with_experts_path_marks_experts_current tests/integration/test_experts_navigation.py::test_experts_navigation_with_authenticated_elena_shows_default_page tests/integration/test_experts_navigation.py::test_experts_navigation_log_story_happy -x

.PHONY: test-experts-s01-browser
test-experts-s01-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_navigation.py::test_experts_navigation_with_sidebar_click_opens_default_page -x

.PHONY: test-experts-s01-log
test-experts-s01-log:
	$(PYTHON) -m pytest tests/integration/test_experts_navigation.py::test_experts_navigation_log_story_happy -x

.PHONY: test-experts-s01-at
test-experts-s01-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S01 -x

.PHONY: test-experts-s01
test-experts-s01:
	+$(MAKE) test-experts-s01-backend
	+$(MAKE) test-experts-s01-at
	+$(MAKE) test-experts-s01-browser
	+$(MAKE) test-experts-s01-log

.PHONY: test-experts-s02-backend
test-experts-s02-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_category_persistence.py::test_category_links_with_design_query_show_five_links_and_one_current tests/integration/test_experts_category_persistence.py::test_category_selection_with_repeated_design_get_remains_current tests/integration/test_experts_category_persistence.py::test_category_selection_log_story_happy -x

.PHONY: test-experts-s02-browser
test-experts-s02-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_category_persistence.py::test_category_navigation_with_reload_and_history_preserves_query -x

.PHONY: test-experts-s02-log
test-experts-s02-log:
	$(PYTHON) -m pytest tests/integration/test_experts_category_persistence.py::test_category_selection_log_story_happy -x

.PHONY: test-experts-s02-at
test-experts-s02-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S02 -x

.PHONY: test-experts-s02
test-experts-s02:
	+$(MAKE) test-experts-s02-backend
	+$(MAKE) test-experts-s02-at
	+$(MAKE) test-experts-s02-browser
	+$(MAKE) test-experts-s02-log

.PHONY: test-experts-s03-backend
test-experts-s03-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_schema.py tests/integration/test_experts_data.py tests/integration/test_experts_list_s03.py tests/unit/test_experts_projection.py tests/unit/test_experts_text.py tests/unit/test_experts_html.py -x

.PHONY: test-experts-s03-browser
test-experts-s03-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_list_s03.py::test_experts_list_with_design_browser_preserves_rank_order -x

.PHONY: test-experts-s03-log
test-experts-s03-log:
	$(PYTHON) -m pytest tests/integration/test_experts_list_s03.py::test_experts_list_with_design_log_story_happy tests/integration/test_experts_list_s03.py::test_list_leaders_with_invalid_category_log_story_reject -x

.PHONY: test-experts-s03-at
test-experts-s03-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S03 -x

.PHONY: test-experts-s03
test-experts-s03:
	+$(MAKE) test-experts-s03-backend
	+$(MAKE) test-experts-s03-at
	+$(MAKE) test-experts-s03-browser
	+$(MAKE) test-experts-s03-log

.PHONY: test-experts-s04-backend
test-experts-s04-backend:
	$(PYTHON) -m pytest tests/integration/test_expert_card_presentation.py::test_present_with_stored_summary_preserves_public_prose tests/integration/test_expert_card_presentation.py::test_present_with_missing_summary_uses_live_numeric_fallback tests/integration/test_expert_card_presentation.py::test_present_with_invalid_projection_rejects_input tests/integration/test_expert_card_presentation.py::test_expert_card_log_story_happy tests/integration/test_expert_card_presentation.py::test_expert_card_log_story_reject tests/integration/test_expert_cards.py::test_experts_card_with_cedar_baseline_shows_readable_signals tests/integration/test_expert_cards.py::test_experts_card_with_stored_caveat_adds_no_suitability_claim tests/integration/test_expert_card_visual_evidence.py::test_experts_cards_with_reviewed_visual_evidence_cover_required_states -x

.PHONY: test-experts-s04-browser
test-experts-s04-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_expert_cards.py::test_experts_cards_with_required_viewports_keep_actions_readable tests/e2e/test_expert_cards.py::test_experts_card_with_view_profile_opens_full_evidence -x

.PHONY: test-experts-s04-log
test-experts-s04-log:
	$(PYTHON) -m pytest tests/integration/test_expert_card_presentation.py::test_expert_card_log_story_happy tests/integration/test_expert_card_presentation.py::test_expert_card_log_story_reject -x

.PHONY: test-experts-s04-at
test-experts-s04-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S04 -x

.PHONY: test-experts-s04
test-experts-s04:
	+$(MAKE) test-experts-s04-backend
	+$(MAKE) test-experts-s04-at
	+$(MAKE) test-experts-s04-browser
	+$(MAKE) test-experts-s04-log

.PHONY: test-experts-s05-backend
test-experts-s05-backend:
	$(PYTHON) -m pytest tests/unit/test_expert_profile_handoff_html.py::test_extract_maria_profile_href_with_invalid_anchor_rejects tests/integration/test_experts_profile_handoff.py::test_maria_profile_handoff_with_design_card_displays_full_paragraph -x

.PHONY: test-experts-s05-browser
test-experts-s05-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_profile_handoff.py::test_maria_profile_handoff_with_browser_click_displays_full_paragraph -x

.PHONY: test-experts-s05-at
test-experts-s05-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S05 -x

.PHONY: test-experts-s05
test-experts-s05:
	+$(MAKE) test-experts-s05-backend
	+$(MAKE) test-experts-s05-at
	+$(MAKE) test-experts-s05-browser

.PHONY: test-experts-s06-backend
test-experts-s06-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_empty_category.py::test_experts_other_with_baseline_renders_exact_empty_state tests/integration/test_experts_empty_category.py::test_experts_design_with_baseline_omits_empty_state -x

.PHONY: test-experts-s06-browser
test-experts-s06-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_empty_category.py::test_experts_other_with_responsive_viewport_shows_empty_state -x

.PHONY: test-experts-s06-at
test-experts-s06-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S06 -x

.PHONY: test-experts-s06
test-experts-s06:
	+$(MAKE) test-experts-s06-backend
	+$(MAKE) test-experts-s06-at
	+$(MAKE) test-experts-s06-browser

.PHONY: test-experts-s07-backend
test-experts-s07-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_guest_contract.py::test_experts_list_with_anonymous_design_request_matches_public_ranking -x

.PHONY: test-experts-s07-browser
test-experts-s07-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_guest.py::test_experts_list_with_guest_browser_shows_public_cards_and_auth_actions -x

.PHONY: test-experts-s07-at
test-experts-s07-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S07 -x

.PHONY: test-experts-s07
test-experts-s07:
	+$(MAKE) test-experts-s07-backend
	+$(MAKE) test-experts-s07-at
	+$(MAKE) test-experts-s07-browser

.PHONY: test-experts-s08-backend
test-experts-s08-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_list_tie.py::test_cedar_tie03_with_real_awards_preserves_sofia_and_matches_equal_totals tests/integration/test_experts_list_tie.py::test_cedar_tie03_with_missing_sofia_rejects_without_partial_writes tests/integration/test_experts_list_tie.py::test_cedar_tie03_with_existing_alina_rejects_without_duplicate_awards tests/integration/test_experts_list_tie.py::test_experts_list_with_equal_totals_orders_username_ascending tests/integration/test_experts_list_tie.py::test_experts_list_with_equal_totals_repeated_requests_preserve_order_and_awards -x

.PHONY: test-experts-s08-browser
test-experts-s08-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_list_tie.py::test_experts_list_with_tie03_browser_preserves_dom_and_visible_rank -x

.PHONY: test-experts-s08-at
test-experts-s08-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S08 -x

.PHONY: test-experts-s08
test-experts-s08:
	+$(MAKE) test-experts-s08-backend
	+$(MAKE) test-experts-s08-at
	+$(MAKE) test-experts-s08-browser

.PHONY: test-experts-s09-backend
test-experts-s09-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_category_fallback.py::test_experts_list_with_unknown_category_returns_development_only tests/integration/test_experts_category_fallback.py::test_experts_list_with_invalid_category_variant_returns_development_only tests/integration/test_experts_category_fallback.py::test_experts_category_fallback_log_story_happy tests/integration/test_experts_category_fallback.py::test_experts_category_fallback_log_story_reject -x

.PHONY: test-experts-s09-browser
test-experts-s09-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_category_fallback.py::test_experts_list_with_unknown_category_survives_browser_refresh -x

.PHONY: test-experts-s09-log
test-experts-s09-log:
	$(PYTHON) -m pytest tests/integration/test_experts_category_fallback.py::test_experts_category_fallback_log_story_happy tests/integration/test_experts_category_fallback.py::test_experts_category_fallback_log_story_reject -x

.PHONY: test-experts-s09-at
test-experts-s09-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S09 -x

.PHONY: test-experts-s09
test-experts-s09:
	+$(MAKE) test-experts-s09-backend
	+$(MAKE) test-experts-s09-at
	+$(MAKE) test-experts-s09-browser
	+$(MAKE) test-experts-s09-log

.PHONY: test-experts-s10-backend
test-experts-s10-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_own_profile.py::test_profile_view_with_maria_adds_contribution_context tests/integration/test_experts_own_profile.py::test_profile_view_with_maria_preserves_account_controls tests/integration/test_experts_own_profile.py::test_profile_view_with_other_subject_query_uses_request_owner tests/integration/test_experts_own_profile.py::test_profile_view_with_missing_expert_profile_preserves_account_page tests/integration/test_experts_own_profile.py::test_profile_view_with_summary_markup_escapes_content tests/integration/test_experts_own_profile.py::test_profile_contribution_context_with_maria_log_story_happy tests/integration/test_experts_own_profile.py::test_profile_contribution_context_with_anonymous_request_log_story_reject tests/integration/test_experts_own_profile.py::test_own_profile_with_zero_karma_renders_neutral_category -x

.PHONY: test-experts-s10-browser
test-experts-s10-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_own_profile.py::test_own_profile_with_maria_renders_signals_and_existing_controls -x

.PHONY: test-experts-s10-log
test-experts-s10-log:
	$(PYTHON) -m pytest tests/integration/test_experts_own_profile.py::test_profile_contribution_context_with_maria_log_story_happy tests/integration/test_experts_own_profile.py::test_profile_contribution_context_with_anonymous_request_log_story_reject -x

.PHONY: test-experts-s10-at
test-experts-s10-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S10 -x

.PHONY: test-experts-s10
test-experts-s10:
	+$(MAKE) test-experts-s10-backend
	+$(MAKE) test-experts-s10-at
	+$(MAKE) test-experts-s10-browser
	+$(MAKE) test-experts-s10-log

.PHONY: test-experts-s11-backend
test-experts-s11-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_profile_summary.py::test_profile_summary_contract_with_seeded_maria_returns_complete_stored_paragraph tests/integration/test_experts_profile_summary.py::test_profile_summary_markup_with_long_paragraph_links_button_to_region -x

.PHONY: test-experts-s11-browser
test-experts-s11-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_profile_summary.py::test_profile_summary_with_long_paragraph_expands_and_collapses tests/e2e/test_experts_profile_summary.py::test_profile_summary_with_keyboard_activation_preserves_focus_and_state tests/e2e/test_experts_profile_summary.py::test_profile_summary_with_short_paragraph_displays_without_unnecessary_toggle -x

.PHONY: test-experts-s11-server
test-experts-s11-server:
	+$(MAKE) test-experts-s11-backend

.PHONY: test-experts-s11
test-experts-s11:
	+$(MAKE) test-experts-s11-backend
	+$(MAKE) test-experts-s11-server
	+$(MAKE) test-experts-s11-browser

.PHONY: test-experts-s12-backend
test-experts-s12-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_profile_sources.py::test_profile_sources_with_cedar_ledger_reconcile tests/integration/test_experts_profile_sources.py::test_profile_sources_with_new_learning_award_refresh_values -x

.PHONY: test-experts-s12-browser
test-experts-s12-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_profile_sources.py::test_profile_sources_with_required_viewports_remain_reconciled -x

.PHONY: test-experts-s12-at
test-experts-s12-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S12 -x

.PHONY: test-experts-s12
test-experts-s12:
	+$(MAKE) test-experts-s12-backend
	+$(MAKE) test-experts-s12-at
	+$(MAKE) test-experts-s12-browser

.PHONY: test-experts-s13-backend
test-experts-s13-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_profile_auth.py::test_own_profile_with_anonymous_request_redirects_without_private_render tests/integration/test_experts_profile_auth.py::test_own_profile_with_followed_anonymous_redirect_shows_login_only -x

.PHONY: test-experts-s13-browser
test-experts-s13-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_profile_auth.py::test_own_profile_with_anonymous_browser_navigation_shows_login_only -x

.PHONY: test-experts-s13-at
test-experts-s13-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S13 -x

.PHONY: test-experts-s13
test-experts-s13:
	+$(MAKE) test-experts-s13-backend
	+$(MAKE) test-experts-s13-at
	+$(MAKE) test-experts-s13-browser

.PHONY: test-experts-s14-backend
test-experts-s14-backend:
	$(PYTHON) -m pytest tests/unit/test_expert_contact_context.py::test_build_expert_contact_context_with_authenticated_request_returns_exact_mailto tests/unit/test_expert_contact_context.py::test_build_expert_contact_context_with_guest_request_does_not_query_email tests/unit/test_expert_contact_context.py::test_build_expert_contact_context_with_unusable_email_disables_handoff tests/unit/test_expert_contact_context.py::test_build_expert_contact_context_with_invalid_boundary_input_raises tests/integration/test_experts_reach_out.py::test_reach_out_with_authenticated_elena_matches_both_surfaces tests/integration/test_experts_reach_out.py::test_reach_out_with_guest_request_excludes_email_on_both_surfaces tests/integration/test_experts_reach_out.py::test_reach_out_with_authenticated_unusable_email_renders_disabled_action tests/integration/test_experts_reach_out.py::test_reach_out_log_story_happy tests/integration/test_experts_reach_out.py::test_reach_out_log_story_reject -x

.PHONY: test-experts-s14-browser
test-experts-s14-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_reach_out.py::test_reach_out_with_authenticated_browser_exposes_exact_destination -x

.PHONY: test-experts-s14-log
test-experts-s14-log:
	$(PYTHON) -m pytest tests/integration/test_experts_reach_out.py::test_reach_out_log_story_happy tests/integration/test_experts_reach_out.py::test_reach_out_log_story_reject -x

.PHONY: test-experts-s14-at
test-experts-s14-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S14 -x

.PHONY: test-experts-s14
test-experts-s14:
	+$(MAKE) test-experts-s14-backend
	+$(MAKE) test-experts-s14-at
	+$(MAKE) test-experts-s14-browser
	+$(MAKE) test-experts-s14-log

.PHONY: test-experts-s15-backend
test-experts-s15-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_guest_list_contact.py::test_guest_list_contact_with_anonymous_request_restricts_contact tests/integration/test_experts_guest_list_contact.py::test_guest_list_contact_with_authenticated_then_guest_requests_does_not_leak_email -x

.PHONY: test-experts-s15-browser
test-experts-s15-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_guest_list_contact.py::test_experts_reach_02_with_guest_activation_explains_restriction -x

.PHONY: test-experts-s15-server
test-experts-s15-server:
	+$(MAKE) test-experts-s15-backend

.PHONY: test-experts-s15
test-experts-s15:
	+$(MAKE) test-experts-s15-backend
	+$(MAKE) test-experts-s15-server
	+$(MAKE) test-experts-s15-browser

.PHONY: test-experts-s16-backend
test-experts-s16-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_guest_detail.py::test_guest_detail_with_anonymous_request_preserves_restricted_contact_and_public_evidence -x

.PHONY: test-experts-s16-browser
test-experts-s16-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_guest_detail.py::test_guest_detail_with_required_viewport_keeps_tooltip_and_evidence_accessible -x

.PHONY: test-experts-s16-at
test-experts-s16-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S16 -x

.PHONY: test-experts-s16
test-experts-s16:
	+$(MAKE) test-experts-s16-backend
	+$(MAKE) test-experts-s16-at
	+$(MAKE) test-experts-s16-browser

.PHONY: test-experts-s17-backend
test-experts-s17-backend:
	$(PYTHON) -m pytest tests/integration/test_expert_detail.py::test_public_detail_with_cedar_maria_returns_identity_and_complete_summary tests/integration/test_expert_detail.py::test_public_detail_with_guest_returns_same_public_identity_and_summary tests/integration/test_expert_detail.py::test_public_detail_with_html_summary_escapes_untrusted_markup tests/integration/test_expert_detail.py::test_public_detail_with_request_preserves_persisted_state tests/integration/test_expert_detail.py::test_public_detail_with_cedar_baseline_exposes_only_public_projection tests/integration/test_expert_detail.py::test_public_detail_log_story_happy -x

.PHONY: test-experts-s17-browser
test-experts-s17-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_expert_detail.py::test_public_detail_with_full_summary_has_no_visual_truncation tests/e2e/test_expert_detail.py::test_public_detail_with_required_viewport_preserves_read_context_recipe -x

.PHONY: test-experts-s17-log
test-experts-s17-log:
	$(PYTHON) -m pytest tests/integration/test_expert_detail.py::test_public_detail_log_story_happy -x

.PHONY: test-experts-s17-at
test-experts-s17-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S17 -x

.PHONY: test-experts-s17
test-experts-s17:
	+$(MAKE) test-experts-s17-backend
	+$(MAKE) test-experts-s17-at
	+$(MAKE) test-experts-s17-browser
	+$(MAKE) test-experts-s17-log

.PHONY: test-experts-s18-backend
test-experts-s18-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_public_score_breakdown.py::test_public_score_breakdown_with_cedar_sources_reconciles tests/integration/test_experts_public_score_breakdown.py::test_public_score_breakdown_with_category_subtotals_keeps_separate_sections tests/integration/test_experts_public_score_breakdown.py::test_public_score_breakdown_with_new_ledger_event_reads_live_totals tests/integration/test_experts_public_score_breakdown.py::test_public_score_breakdown_with_repeated_get_preserves_domain_state tests/integration/test_experts_s18_behave.py::test_s18_behave_contract_with_exact_name_executes_without_skips -x

.PHONY: test-experts-s18-browser
test-experts-s18-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_public_score_breakdown.py::test_public_score_breakdown_with_required_viewport_stays_readable -x

.PHONY: test-experts-s18-at
test-experts-s18-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S18 -x

.PHONY: test-experts-s18
test-experts-s18:
	+$(MAKE) test-experts-s18-backend
	+$(MAKE) test-experts-s18-at
	+$(MAKE) test-experts-s18-browser

.PHONY: test-experts-s19-backend
test-experts-s19-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_public_evidence.py::test_public_evidence_with_cedar_release_links_existing_detail_route tests/integration/test_experts_public_evidence.py::test_public_evidence_with_followed_workflow_exposes_cedar_activities -x

.PHONY: test-experts-s19-browser
test-experts-s19-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_public_evidence.py::test_public_evidence_with_real_browser_navigation_reaches_cedar_workflow -x

.PHONY: test-experts-s19-at
test-experts-s19-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S19 -x

.PHONY: test-experts-s19
test-experts-s19:
	+$(MAKE) test-experts-s19-backend
	+$(MAKE) test-experts-s19-at
	+$(MAKE) test-experts-s19-browser

.PHONY: test-experts-s20-backend
test-experts-s20-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_public_privacy.py::test_public_detail_with_anonymous_viewer_excludes_private_data tests/integration/test_experts_public_privacy.py::test_public_detail_with_authenticated_elena_preserves_public_boundary tests/integration/test_experts_public_privacy.py::test_public_detail_with_unpublished_evidence_excludes_each_status tests/integration/test_experts_public_privacy.py::test_public_detail_with_private_fixture_has_allowlisted_projection -x

.PHONY: test-experts-s20-browser
test-experts-s20-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_public_privacy.py::test_public_detail_with_guest_browser_omits_private_markup -x

.PHONY: test-experts-s20-at
test-experts-s20-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S20 -x

.PHONY: test-experts-s20
test-experts-s20:
	+$(MAKE) test-experts-s20-backend
	+$(MAKE) test-experts-s20-at
	+$(MAKE) test-experts-s20-browser

.PHONY: test-experts-s21-backend
test-experts-s21-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_not_found.py::test_expert_detail_with_missing_or_zero_karma_subject_returns_404 tests/integration/test_experts_not_found.py::test_expert_detail_with_ineligible_subject_hides_account_existence tests/integration/test_experts_not_found.py::test_expert_detail_with_rejected_subject_log_story_reject -x

.PHONY: test-experts-s21-browser
test-experts-s21-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_not_found.py::test_expert_detail_with_missing_or_zero_karma_subject_browser_returns_404 -x

.PHONY: test-experts-s21-log
test-experts-s21-log:
	$(PYTHON) -m pytest tests/integration/test_experts_not_found.py::test_expert_detail_with_rejected_subject_log_story_reject -x

.PHONY: test-experts-s21-at
test-experts-s21-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S21 -x

.PHONY: test-experts-s21
test-experts-s21:
	+$(MAKE) test-experts-s21-backend
	+$(MAKE) test-experts-s21-at
	+$(MAKE) test-experts-s21-browser
	+$(MAKE) test-experts-s21-log

.PHONY: test-experts-s22-backend
test-experts-s22-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_empty_evidence.py::test_expert_detail_with_positive_sam_without_public_playbooks_returns_profile tests/integration/test_experts_empty_evidence.py::test_expert_detail_with_only_ineligible_current_playbook_keeps_positive_profile -x

.PHONY: test-experts-s22-browser
test-experts-s22-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_empty_evidence.py::test_expert_detail_with_positive_sam_shows_empty_evidence_in_browser -x

.PHONY: test-experts-s22-at
test-experts-s22-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S22 -x

.PHONY: test-experts-s22
test-experts-s22:
	+$(MAKE) test-experts-s22-backend
	+$(MAKE) test-experts-s22-at
	+$(MAKE) test-experts-s22-browser

.PHONY: test-experts-s23-backend
test-experts-s23-backend:
	$(PYTHON) -m pytest tests/unit/test_contribution_summary_adapter.py::test_s23_normalize_response_with_text_and_usage_returns_port_response tests/unit/test_contribution_summary_adapter.py::test_s23_adapter_with_invalid_request_rejects_before_provider tests/integration/test_experts_summary_submission.py::test_s23_submit_for_review_with_add_activity_refreshes_without_acceptance_award tests/integration/test_experts_summary_submission.py::test_s23_submit_for_review_with_invalid_actor_requests_no_summary tests/integration/test_experts_summary_submission.py::test_s23_submit_for_review_with_rollback_does_not_dispatch_processing tests/integration/test_experts_summary_submission.py::test_s23_http_submission_with_request_id_uses_normal_lifecycle tests/integration/test_experts_summary_submission.py::test_s23_summary_log_story_happy tests/integration/test_experts_summary_submission.py::test_s23_summary_log_story_reject tests/integration/test_experts_summary_proofs.py::test_s23_submission_agent_story_happy tests/integration/test_experts_summary_proofs.py::test_s23_submission_agent_story_reject tests/integration/test_experts_summary_proofs.py::test_s23_submission_with_private_sentinels_agent_story_happy tests/integration/test_experts_summary_proofs.py::test_s23_summary_interaction_agent_story_happy tests/unit/test_contribution_summary_adapter.py::test_s23_normalize_response_with_empty_or_truncated_text_preserves_usage -x

.PHONY: test-experts-s23-log
test-experts-s23-log:
	$(PYTHON) -m pytest tests/integration/test_experts_summary_submission.py::test_s23_summary_log_story_happy tests/integration/test_experts_summary_submission.py::test_s23_summary_log_story_reject -x

.PHONY: test-experts-s23-agent
test-experts-s23-agent:
	$(PYTHON) -m pytest tests/integration/test_experts_summary_proofs.py::test_s23_submission_agent_story_happy tests/integration/test_experts_summary_proofs.py::test_s23_submission_agent_story_reject tests/integration/test_experts_summary_proofs.py::test_s23_submission_with_private_sentinels_agent_story_happy tests/integration/test_experts_summary_proofs.py::test_s23_summary_interaction_agent_story_happy -x

.PHONY: test-experts-s23-at
test-experts-s23-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S23 -x

.PHONY: test-experts-s23
test-experts-s23:
	+$(MAKE) test-experts-s23-backend
	+$(MAKE) test-experts-s23-at
	+$(MAKE) test-experts-s23-log
	+$(MAKE) test-experts-s23-agent

.PHONY: test-experts-s24-backend
test-experts-s24-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_stored_summary.py::test_stored_summary_with_three_surface_reads_preserves_identical_full_text tests/integration/test_experts_stored_summary.py::test_stored_summary_with_repeated_reads_preserves_refresh_state -x

.PHONY: test-experts-s24-browser
test-experts-s24-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_stored_summary.py::test_stored_summary_with_target_viewport_preserves_visual_contract -x

.PHONY: test-experts-s24-server
test-experts-s24-server:
	+$(MAKE) test-experts-s24-backend

.PHONY: test-experts-s24
test-experts-s24:
	+$(MAKE) test-experts-s24-backend
	+$(MAKE) test-experts-s24-server
	+$(MAKE) test-experts-s24-browser

.PHONY: test-experts-s25-backend
test-experts-s25-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_summary_resubmission.py::test_s25_resubmit_with_reviewed_pip_refreshes_without_award tests/integration/test_experts_summary_resubmission.py::test_s25_resubmit_with_identical_valid_summary_records_new_refresh tests/integration/test_experts_summary_resubmission.py::test_s25_submit_with_reviewed_or_foreign_actor_rejects_before_refresh tests/integration/test_experts_summary_resubmission.py::test_s25_http_withdraw_and_resubmit_uses_existing_post_routes tests/integration/test_experts_summary_resubmission.py::test_s25_resubmission_log_story_happy tests/integration/test_experts_summary_resubmission.py::test_s25_resubmission_log_story_reject tests/integration/test_experts_summary_proofs.py::test_s25_resubmission_agent_story_happy tests/integration/test_experts_summary_proofs.py::test_s25_resubmission_agent_story_reject -x

.PHONY: test-experts-s25-browser
test-experts-s25-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_summary_resubmission.py::test_s25_browser_withdraw_and_resubmit_refreshes_before_decision -x

.PHONY: test-experts-s25-log
test-experts-s25-log:
	$(PYTHON) -m pytest tests/integration/test_experts_summary_resubmission.py::test_s25_resubmission_log_story_happy tests/integration/test_experts_summary_resubmission.py::test_s25_resubmission_log_story_reject -x

.PHONY: test-experts-s25-agent
test-experts-s25-agent:
	$(PYTHON) -m pytest tests/integration/test_experts_summary_proofs.py::test_s25_resubmission_agent_story_happy tests/integration/test_experts_summary_proofs.py::test_s25_resubmission_agent_story_reject -x

.PHONY: test-experts-s25-at
test-experts-s25-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S25 -x

.PHONY: test-experts-s25
test-experts-s25:
	+$(MAKE) test-experts-s25-backend
	+$(MAKE) test-experts-s25-at
	+$(MAKE) test-experts-s25-browser
	+$(MAKE) test-experts-s25-log
	+$(MAKE) test-experts-s25-agent

.PHONY: test-experts-s26-backend
test-experts-s26-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_numeric_fallback.py::test_numeric_fallback_with_cedar_mike_uses_live_counts tests/integration/test_experts_numeric_fallback.py::test_numeric_fallback_with_playbook_visibility_changes_refreshes_next_request tests/integration/test_experts_numeric_fallback.py::test_numeric_fallback_with_ledger_changes_counts_only_gui_author_consumption tests/integration/test_experts_numeric_fallback.py::test_numeric_fallback_with_missing_summary_is_consistent_across_surfaces tests/integration/test_experts_numeric_fallback.py::test_numeric_fallback_with_repeated_gets_preserves_summary_and_generation_history tests/integration/test_experts_numeric_fallback.py::test_numeric_fallback_log_story_happy -x

.PHONY: test-experts-s26-browser
test-experts-s26-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_numeric_fallback.py::test_numeric_fallback_with_reload_shows_updated_live_counts tests/e2e/test_experts_numeric_fallback.py::test_numeric_fallback_with_own_profile_shows_no_expansion_control -x

.PHONY: test-experts-s26-log
test-experts-s26-log:
	$(PYTHON) -m pytest tests/integration/test_experts_numeric_fallback.py::test_numeric_fallback_log_story_happy -x

.PHONY: test-experts-s26-at
test-experts-s26-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S26 -x

.PHONY: test-experts-s26
test-experts-s26:
	+$(MAKE) test-experts-s26-backend
	+$(MAKE) test-experts-s26-at
	+$(MAKE) test-experts-s26-browser
	+$(MAKE) test-experts-s26-log

.PHONY: test-experts-s27-backend
test-experts-s27-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_public_evidence.py::test_collect_with_cedar_privacy_variant_returns_only_published_public_facts tests/integration/test_experts_public_evidence.py::test_collect_with_partial_or_unpublished_decisions_excludes_ineligible_changes tests/integration/test_experts_public_evidence.py::test_collect_with_invalid_subject_rejects_before_model_call tests/integration/test_experts_public_evidence.py::test_build_summary_prompt_with_public_evidence_preserves_layers_and_bounds tests/integration/test_experts_public_evidence.py::test_validate_summary_response_with_boundary_or_unsafe_output_enforces_contract tests/integration/test_experts_public_evidence.py::test_public_evidence_log_story_happy tests/integration/test_experts_public_evidence.py::test_public_evidence_log_story_reject tests/integration/test_experts_summary_proofs.py::test_s27_summary_agent_story_happy tests/integration/test_experts_summary_proofs.py::test_s27_summary_agent_story_reject tests/integration/test_experts_summary_proofs.py::test_s27_summary_with_exhausted_script_fails_loudly tests/unit/test_agent_test_support.py::test_scripted_llm_with_recorded_call_preserves_request_and_exhaustion -x

.PHONY: test-experts-s27-log
test-experts-s27-log:
	$(PYTHON) -m pytest tests/integration/test_experts_public_evidence.py::test_public_evidence_log_story_happy tests/integration/test_experts_public_evidence.py::test_public_evidence_log_story_reject tests/integration/test_experts_summary_proofs.py::test_s27_summary_log_story_happy tests/integration/test_experts_summary_proofs.py::test_s27_summary_log_story_reject -x

.PHONY: test-experts-s27-agent
test-experts-s27-agent:
	$(PYTHON) -m pytest tests/integration/test_experts_summary_proofs.py::test_s27_summary_agent_story_happy tests/integration/test_experts_summary_proofs.py::test_s27_summary_agent_story_reject tests/integration/test_experts_summary_proofs.py::test_s27_summary_with_exhausted_script_fails_loudly -x

.PHONY: test-experts-s27-at
test-experts-s27-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S27 -x

.PHONY: test-experts-s27
test-experts-s27:
	+$(MAKE) test-experts-s27-backend
	+$(MAKE) test-experts-s27-at
	+$(MAKE) test-experts-s27-log
	+$(MAKE) test-experts-s27-agent

.PHONY: test-experts-s28-backend
test-experts-s28-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_summary_stability.py::test_s28_copy_receipt_with_stored_summary_updates_only_live_numbers tests/integration/test_experts_summary_stability.py::test_s28_display_with_completed_copy_reads_live_totals_and_stored_prose tests/integration/test_experts_summary_stability.py::test_s28_copy_log_story_happy tests/integration/test_experts_summary_proofs.py::test_s28_points_change_agent_story_happy -x

.PHONY: test-experts-s28-browser
test-experts-s28-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_summary_stability.py::test_s28_browser_with_successful_copy_updates_score_and_preserves_paragraph -x

.PHONY: test-experts-s28-log
test-experts-s28-log:
	$(PYTHON) -m pytest tests/integration/test_experts_summary_stability.py::test_s28_copy_log_story_happy -x

.PHONY: test-experts-s28-agent
test-experts-s28-agent:
	$(PYTHON) -m pytest tests/integration/test_experts_summary_proofs.py::test_s28_points_change_agent_story_happy -x

.PHONY: test-experts-s28-at
test-experts-s28-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S28 -x

.PHONY: test-experts-s28
test-experts-s28:
	+$(MAKE) test-experts-s28-backend
	+$(MAKE) test-experts-s28-at
	+$(MAKE) test-experts-s28-browser
	+$(MAKE) test-experts-s28-log
	+$(MAKE) test-experts-s28-agent

.PHONY: test-experts-s29-backend
test-experts-s29-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_summary_failure.py::test_s29_submission_with_summary_failure_retains_last_good tests/integration/test_experts_summary_failure.py::test_s29_submission_with_summary_failure_continues_existing_assessment tests/integration/test_experts_summary_failure.py::test_s29_submission_with_assessment_failure_uses_existing_retry tests/integration/test_experts_summary_failure.py::test_s29_submission_with_missing_last_good_preserves_empty_state tests/integration/test_experts_summary_failure.py::test_s29_summary_log_story_reject tests/integration/test_experts_summary_proofs.py::test_s29_summary_agent_story_reject tests/integration/test_experts_summary_proofs.py::test_s29_summary_interaction_with_failure_preserves_usage_agent_story_reject tests/integration/test_experts_summary_proofs.py::test_s29_summary_with_exhausted_script_fails_loudly -x

.PHONY: test-experts-s29-log
test-experts-s29-log:
	$(PYTHON) -m pytest tests/integration/test_experts_summary_failure.py::test_s29_summary_log_story_reject -x

.PHONY: test-experts-s29-agent
test-experts-s29-agent:
	$(PYTHON) -m pytest tests/integration/test_experts_summary_proofs.py::test_s29_summary_agent_story_reject tests/integration/test_experts_summary_proofs.py::test_s29_summary_interaction_with_failure_preserves_usage_agent_story_reject tests/integration/test_experts_summary_proofs.py::test_s29_summary_with_exhausted_script_fails_loudly -x

.PHONY: test-experts-s29-at
test-experts-s29-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S29 -x

.PHONY: test-experts-s29
test-experts-s29:
	+$(MAKE) test-experts-s29-backend
	+$(MAKE) test-experts-s29-at
	+$(MAKE) test-experts-s29-log
	+$(MAKE) test-experts-s29-agent

.PHONY: test-experts-s30-backend
test-experts-s30-backend:
	$(PYTHON) -m pytest tests/unit/test_karma_release_service.py::test_award_first_release_with_v1_release_creates_5000_category_snapshot tests/unit/test_karma_release_service.py::test_award_first_release_with_same_receipt_returns_existing_award tests/unit/test_karma_release_service.py::test_persist_awards_with_invalid_input_rejects_without_writes tests/unit/test_karma_release_service.py::test_persist_awards_with_reused_identity_and_changed_payload_rejects tests/unit/test_karma_release_service.py::test_release_with_outer_transaction_rollback_removes_version_and_award tests/unit/test_karma_release_service.py::test_release_with_preexisting_history_and_no_ledger_does_not_backfill tests/unit/test_karma_release_service.py::test_release_with_rejected_precondition_preserves_draft_and_empty_ledger tests/unit/test_karma_release_service.py::test_release_with_legacy_entrypoint_preserves_playbook_return_contract tests/integration/test_experts_release_acceptance.py::test_karma_release_01_with_baseline_displays_award_and_product_ranking tests/integration/test_experts_release_acceptance.py::test_release_with_nonfirst_outcome_omits_earned_message tests/integration/test_experts_release_log_story.py::test_karma_release_log_story_happy tests/integration/test_experts_release_log_story.py::test_karma_release_log_story_reject tests/integration/test_experts_release_log_story.py::test_karma_release_log_story_duplicate -x

.PHONY: test-experts-s30-browser
test-experts-s30-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_release.py::test_karma_release_01_with_browser_shows_award_and_product_order -x

.PHONY: test-experts-s30-log
test-experts-s30-log:
	$(PYTHON) -m pytest tests/integration/test_experts_release_log_story.py::test_karma_release_log_story_happy tests/integration/test_experts_release_log_story.py::test_karma_release_log_story_reject tests/integration/test_experts_release_log_story.py::test_karma_release_log_story_duplicate -x

.PHONY: test-experts-s30-at
test-experts-s30-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S30 -x

.PHONY: test-experts-s30
test-experts-s30:
	+$(MAKE) test-experts-s30-backend
	+$(MAKE) test-experts-s30-at
	+$(MAKE) test-experts-s30-browser
	+$(MAKE) test-experts-s30-log

.PHONY: test-experts-s31-backend
test-experts-s31-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_release_later_versions.py::test_later_major_with_accepted_pip_preserves_first_release_award tests/integration/test_experts_release_later_versions.py::test_later_major_with_normal_releases_preserves_single_award tests/integration/test_experts_release_later_versions.py::test_later_major_with_staff_revert_and_release_preserves_single_award tests/integration/test_experts_release_later_versions.py::test_later_major_with_imported_release_marker_preserves_history tests/integration/test_experts_release_later_versions.py::test_later_major_with_changed_author_preserves_original_recipient tests/integration/test_experts_release_later_versions.py::test_later_major_with_denied_operations_preserves_version_and_award tests/integration/test_experts_release_later_log_story.py::test_karma_later_release_log_story_happy tests/integration/test_experts_release_later_log_story.py::test_karma_later_release_log_story_reject -x

.PHONY: test-experts-s31-browser
test-experts-s31-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_release_later_versions.py::test_later_major_with_browser_release_omits_second_award_message -x

.PHONY: test-experts-s31-log
test-experts-s31-log:
	$(PYTHON) -m pytest tests/integration/test_experts_release_later_log_story.py::test_karma_later_release_log_story_happy tests/integration/test_experts_release_later_log_story.py::test_karma_later_release_log_story_reject -x

.PHONY: test-experts-s31-at
test-experts-s31-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S31 -x

.PHONY: test-experts-s31
test-experts-s31:
	+$(MAKE) test-experts-s31-backend
	+$(MAKE) test-experts-s31-at
	+$(MAKE) test-experts-s31-browser
	+$(MAKE) test-experts-s31-log

.PHONY: test-experts-s32-backend
test-experts-s32-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_karma_pip.py::test_finalize_pip_with_major_add_awards_submitter_and_publishes_once tests/integration/test_experts_karma_pip.py::test_award_accepted_changes_with_retry_preserves_original_event tests/integration/test_experts_karma_pip.py::test_finalize_pip_with_outer_rollback_restores_content_version_decision_and_awards tests/integration/test_experts_karma_pip.py::test_finalize_pip_with_invalid_apply_creates_no_award_or_email tests/integration/test_experts_karma_pip.py::test_accepted_change_policy_with_unsupported_change_returns_no_award tests/integration/test_experts_karma_pip.py::test_award_accepted_changes_with_ineligible_context_returns_no_awards tests/integration/test_experts_karma_pip.py::test_accepted_change_log_story_happy tests/integration/test_experts_karma_pip.py::test_accepted_change_log_story_reject -x

.PHONY: test-experts-s32-browser
test-experts-s32-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_karma_pip.py::test_admin_browser_with_major_add_finalization_awards_maria -x

.PHONY: test-experts-s32-log
test-experts-s32-log:
	$(PYTHON) -m pytest tests/integration/test_experts_karma_pip.py::test_accepted_change_log_story_happy tests/integration/test_experts_karma_pip.py::test_accepted_change_log_story_reject -x

.PHONY: test-experts-s32-at
test-experts-s32-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S32 -x

.PHONY: test-experts-s32
test-experts-s32:
	+$(MAKE) test-experts-s32-backend
	+$(MAKE) test-experts-s32-at
	+$(MAKE) test-experts-s32-browser
	+$(MAKE) test-experts-s32-log

.PHONY: test-experts-s33-backend
test-experts-s33-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_karma_minor_pip.py::test_minor_case_matrix_with_literal_examples_matches_all_twenty_rows tests/integration/test_experts_karma_minor_pip.py::test_finalize_pip_with_each_minor_change_applies_once_and_awards_submitter tests/integration/test_experts_karma_minor_pip.py::test_finalize_pip_with_minor_service_call_preserves_proposal_return tests/integration/test_experts_karma_minor_pip.py::test_finalize_pip_with_nonstaff_preserves_minor_target_and_ledger tests/integration/test_experts_karma_minor_pip.py::test_minor_fixture_with_unknown_or_major_row_rejects_before_writes tests/integration/test_experts_karma_minor_pip.py::test_minor_acceptance_log_story_happy -x

.PHONY: test-experts-s33-log
test-experts-s33-log:
	$(PYTHON) -m pytest tests/integration/test_experts_karma_minor_pip.py::test_minor_acceptance_log_story_happy -x

.PHONY: test-experts-s33-at
test-experts-s33-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S33 -x

.PHONY: test-experts-s33
test-experts-s33:
	+$(MAKE) test-experts-s33-backend
	+$(MAKE) test-experts-s33-at
	+$(MAKE) test-experts-s33-log

.PHONY: test-experts-s34-backend
test-experts-s34-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_karma_partial.py::test_partial_fixture_with_reviewed_state_preserves_baseline tests/integration/test_experts_karma_partial.py::test_finalize_partial_with_accepted_add_awards_only_500 tests/integration/test_experts_karma_partial.py::test_finalize_partial_with_outer_commit_sends_one_normal_notification tests/integration/test_experts_karma_partial.py::test_finalize_partial_with_outer_rollback_preserves_baseline_and_sends_no_mail tests/integration/test_experts_karma_partial.py::test_partial_decision_log_story_happy tests/integration/test_experts_karma_partial.py::test_partial_decision_log_story_reject -x

.PHONY: test-experts-s34-log
test-experts-s34-log:
	$(PYTHON) -m pytest tests/integration/test_experts_karma_partial.py::test_partial_decision_log_story_happy tests/integration/test_experts_karma_partial.py::test_partial_decision_log_story_reject -x

.PHONY: test-experts-s34-at
test-experts-s34-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S34 -x

.PHONY: test-experts-s34
test-experts-s34:
	+$(MAKE) test-experts-s34-backend
	+$(MAKE) test-experts-s34-at
	+$(MAKE) test-experts-s34-log

.PHONY: test-experts-s35-backend
test-experts-s35-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_karma_nonaccepted.py::test_nonaccepted_pip_log_story_reject tests/integration/test_experts_karma_nonaccepted.py::test_finalize_pip_with_rejected_only_preserves_karma_content_and_version tests/integration/test_experts_karma_nonaccepted.py::test_rejected_finalization_log_story_reject -x

.PHONY: test-experts-s35-log
test-experts-s35-log:
	$(PYTHON) -m pytest tests/integration/test_experts_karma_nonaccepted.py::test_nonaccepted_pip_log_story_reject tests/integration/test_experts_karma_nonaccepted.py::test_rejected_finalization_log_story_reject -x

.PHONY: test-experts-s35-at
test-experts-s35-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S35 -x

.PHONY: test-experts-s35
test-experts-s35:
	+$(MAKE) test-experts-s35-backend
	+$(MAKE) test-experts-s35-at
	+$(MAKE) test-experts-s35-log

.PHONY: test-experts-s36-backend
test-experts-s36-backend:
	$(PYTHON) -m pytest tests/integration/test_karma_copy.py::test_award_successful_consumption_with_other_author_creates_atomic_pair tests/integration/test_karma_copy.py::test_copy_receipt_with_authenticated_authorized_activity_credits_both tests/integration/test_karma_copy.py::test_copy_receipt_with_render_only_creates_no_awards tests/integration/test_karma_copy.py::test_copy_receipt_with_forbidden_fields_rejects_request tests/integration/test_karma_copy.py::test_copy_receipt_with_unauthorized_entity_creates_no_awards tests/integration/test_karma_copy.py::test_copy_receipt_with_missing_csrf_rejects_request tests/integration/test_karma_copy.py::test_copy_receipt_log_story_happy tests/integration/test_karma_copy.py::test_copy_receipt_log_story_reject -x

.PHONY: test-experts-s36-browser
test-experts-s36-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_karma_copy.py::test_copy_prompt_with_maria_copies_actual_prompt_and_credits_pair tests/e2e/test_karma_copy.py::test_copy_prompt_with_list_and_embed_surfaces_reports_same_entity -x

.PHONY: test-experts-s36-log
test-experts-s36-log:
	$(PYTHON) -m pytest tests/integration/test_karma_copy.py::test_copy_receipt_log_story_happy tests/integration/test_karma_copy.py::test_copy_receipt_log_story_reject -x

.PHONY: test-experts-s36-server
test-experts-s36-server:
	+$(MAKE) test-experts-s36-backend

.PHONY: test-experts-s36
test-experts-s36:
	+$(MAKE) test-experts-s36-backend
	+$(MAKE) test-experts-s36-server
	+$(MAKE) test-experts-s36-browser
	+$(MAKE) test-experts-s36-log

.PHONY: test-experts-s37-backend
test-experts-s37-backend:
	$(PYTHON) -m pytest tests/integration/test_karma_guest_copy.py::test_guest_activity_with_initial_get_renders_full_prompt_without_awards tests/integration/test_karma_guest_copy.py::test_guest_copy_receipt_with_anonymous_post_rejects_without_awards tests/integration/test_karma_guest_copy.py::test_guest_copy_receipt_log_story_reject -x

.PHONY: test-experts-s37-browser
test-experts-s37-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_karma_guest_copy.py::test_guest_copy_with_public_activity_copies_full_prompt_without_receipt_or_awards -x

.PHONY: test-experts-s37-log
test-experts-s37-log:
	$(PYTHON) -m pytest tests/integration/test_karma_guest_copy.py::test_guest_copy_receipt_log_story_reject -x

.PHONY: test-experts-s37-server
test-experts-s37-server:
	+$(MAKE) test-experts-s37-backend

.PHONY: test-experts-s37
test-experts-s37:
	+$(MAKE) test-experts-s37-backend
	+$(MAKE) test-experts-s37-server
	+$(MAKE) test-experts-s37-browser
	+$(MAKE) test-experts-s37-log

.PHONY: test-experts-s38-backend
test-experts-s38-backend:
	$(PYTHON) -m pytest tests/integration/test_karma_copy.py::test_award_successful_consumption_with_self_activity_returns_no_awards tests/integration/test_karma_copy.py::test_copy_receipt_with_self_activity_returns_successful_exclusion tests/integration/test_karma_copy.py::test_copy_receipt_with_self_activity_without_csrf_returns_forbidden tests/integration/test_karma_copy.py::test_copy_receipt_with_self_activity_log_story_happy -x

.PHONY: test-experts-s38-browser
test-experts-s38-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_karma_copy.py::test_copy_prompt_with_mike_copies_actual_prompt_without_awards tests/e2e/test_karma_copy.py::test_copy_uat_with_independent_baseline_lanes_matches_contract -x

.PHONY: test-experts-s38-log
test-experts-s38-log:
	$(PYTHON) -m pytest tests/integration/test_karma_copy.py::test_copy_receipt_with_self_activity_log_story_happy -x

.PHONY: test-experts-s38-server
test-experts-s38-server:
	+$(MAKE) test-experts-s38-backend

.PHONY: test-experts-s38
test-experts-s38:
	+$(MAKE) test-experts-s38-backend
	+$(MAKE) test-experts-s38-server
	+$(MAKE) test-experts-s38-browser
	+$(MAKE) test-experts-s38-log

.PHONY: test-experts-s39-backend
test-experts-s39-backend:
	$(PYTHON) -m pytest tests/integration/test_karma_mcp.py::test_mcp_detail_with_authorized_fixture_returns_content_and_pair tests/integration/test_karma_mcp.py::test_consumption_service_with_authorized_fixture_records_pair tests/integration/test_karma_mcp.py::test_mcp_detail_with_legacy_registration_returns_content_and_pair tests/integration/test_karma_mcp.py::test_mcp_detail_with_stdio_transport_returns_clean_jsonrpc tests/integration/test_karma_mcp.py::test_detail_rest_get_with_authorized_token_does_not_award tests/integration/test_karma_mcp.py::test_consumption_receipt_with_invalid_request_rejects_without_awards tests/integration/test_karma_mcp.py::test_consumption_receipt_with_retry_preserves_awards_and_timestamp tests/integration/test_karma_mcp.py::test_mcp_detail_with_history_options_records_one_pair tests/integration/test_karma_mcp.py::test_mcp_detail_log_story_happy tests/integration/test_karma_mcp.py::test_mcp_detail_log_story_reject tests/integration/test_karma_mcp.py::test_mcp_client_factory_with_different_actors_restores_context_and_auth tests/integration/test_karma_mcp.py::test_legacy_detail_and_collections_with_async_guard_use_safe_orm tests/integration/test_karma_mcp.py::test_set_current_user_with_account_metadata_logs_only_safe_context tests/integration/test_karma_mcp.py::test_phase_detail_with_actor_email_logs_only_identifiers -x

.PHONY: test-experts-s39-log
test-experts-s39-log:
	$(PYTHON) -m pytest tests/integration/test_karma_mcp.py::test_mcp_detail_log_story_happy tests/integration/test_karma_mcp.py::test_mcp_detail_log_story_reject tests/integration/test_karma_mcp.py::test_set_current_user_with_account_metadata_logs_only_safe_context tests/integration/test_karma_mcp.py::test_phase_detail_with_actor_email_logs_only_identifiers -x

.PHONY: test-experts-s39-at
test-experts-s39-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S39 -x

.PHONY: test-experts-s39
test-experts-s39:
	+$(MAKE) test-experts-s39-backend
	+$(MAKE) test-experts-s39-at
	+$(MAKE) test-experts-s39-log

.PHONY: test-experts-s40-backend
test-experts-s40-backend:
	$(PYTHON) -m pytest tests/integration/test_karma_mcp_self_fetch.py::test_self_fetch_with_registered_facade_returns_content_without_awards tests/integration/test_karma_mcp_self_fetch.py::test_self_fetch_with_shared_service_returns_no_awards tests/integration/test_karma_mcp_self_fetch.py::test_self_fetch_with_registered_legacy_returns_content_without_awards tests/integration/test_karma_mcp_self_fetch.py::test_self_fetch_with_facade_stdio_returns_clean_protocol_without_awards tests/integration/test_karma_mcp_self_fetch.py::test_self_fetch_with_bare_rest_get_does_not_award tests/integration/test_karma_mcp_self_fetch.py::test_self_fetch_with_forged_actor_receipt_rejects_without_awards tests/integration/test_karma_mcp_self_fetch.py::test_self_fetch_with_target_author_without_pip_permission_rejects tests/integration/test_karma_mcp_self_fetch.py::test_self_fetch_log_story_happy tests/integration/test_karma_mcp_self_fetch.py::test_self_fetch_log_story_reject tests/integration/test_karma_mcp_self_fetch.py::test_self_fetch_acceptance_with_exact_outline_executes_ten_rows -x

.PHONY: test-experts-s40-log
test-experts-s40-log:
	$(PYTHON) -m pytest tests/integration/test_karma_mcp_self_fetch.py::test_self_fetch_log_story_happy tests/integration/test_karma_mcp_self_fetch.py::test_self_fetch_log_story_reject -x

.PHONY: test-experts-s40-at
test-experts-s40-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S40 -x

.PHONY: test-experts-s40
test-experts-s40:
	+$(MAKE) test-experts-s40-backend
	+$(MAKE) test-experts-s40-at
	+$(MAKE) test-experts-s40-log

.PHONY: test-experts-s41-backend
test-experts-s41-backend:
	$(PYTHON) -m pytest tests/integration/test_karma_mcp_collections.py::test_collection_with_registered_tool_preserves_metadata_and_state tests/integration/test_karma_mcp_collections.py::test_collection_with_direct_service_preserves_awards tests/integration/test_karma_mcp_collections.py::test_collection_with_plain_rest_preserves_awards tests/integration/test_karma_mcp_collections.py::test_collection_with_empty_or_denied_scope_preserves_awards tests/integration/test_karma_mcp_collections.py::test_collection_with_stdio_entrypoint_preserves_protocol_and_state tests/integration/test_karma_mcp_collections.py::test_collection_log_story_happy tests/integration/test_karma_mcp_collections.py::test_collection_with_exact_acceptance_executes_one_contract -x

.PHONY: test-experts-s41-log
test-experts-s41-log:
	$(PYTHON) -m pytest tests/integration/test_karma_mcp_collections.py::test_collection_log_story_happy -x

.PHONY: test-experts-s41-at
test-experts-s41-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S41 -x

.PHONY: test-experts-s41
test-experts-s41:
	+$(MAKE) test-experts-s41-backend
	+$(MAKE) test-experts-s41-at
	+$(MAKE) test-experts-s41-log

.PHONY: test-experts-s42-backend
test-experts-s42-backend:
	$(PYTHON) -m pytest tests/integration/test_karma_exports.py::test_karma_export_facade_t1_with_multiple_files_awards_one_pair tests/integration/test_karma_exports.py::test_karma_export_service_t2_with_multiple_files_awards_one_pair tests/integration/test_karma_exports.py::test_karma_export_with_mirrors_and_ade_files_awards_one_pair tests/integration/test_karma_exports.py::test_karma_export_with_second_independent_call_creates_new_identity tests/integration/test_karma_exports.py::test_karma_export_bundle_with_generation_only_creates_no_awards tests/integration/test_karma_exports.py::test_karma_export_with_receipt_replay_preserves_single_pair tests/integration/test_karma_exports.py::test_karma_export_with_escaping_folder_or_symlink_rejects_before_write tests/integration/test_karma_exports.py::test_karma_export_with_partial_file_failure_creates_no_receipt tests/integration/test_karma_exports.py::test_karma_export_stdio_t3_with_success_returns_clean_jsonrpc tests/integration/test_karma_exports.py::test_karma_export_log_story_happy tests/integration/test_karma_exports.py::test_karma_export_log_story_reject -x

.PHONY: test-experts-s42-log
test-experts-s42-log:
	$(PYTHON) -m pytest tests/integration/test_karma_exports.py::test_karma_export_log_story_happy tests/integration/test_karma_exports.py::test_karma_export_log_story_reject -x

.PHONY: test-experts-s42-at
test-experts-s42-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S42 -x

.PHONY: test-experts-s42
test-experts-s42:
	+$(MAKE) test-experts-s42-backend
	+$(MAKE) test-experts-s42-at
	+$(MAKE) test-experts-s42-log

.PHONY: test-experts-s43-backend
test-experts-s43-backend:
	$(PYTHON) -m pytest tests/integration/test_karma_exports.py::test_self_export_facade_t1_with_owned_content_writes_files_without_awards tests/integration/test_karma_exports.py::test_self_export_legacy_t1_with_owned_content_writes_files_without_awards tests/integration/test_karma_exports.py::test_self_export_service_t2_with_owned_content_writes_files_without_awards tests/integration/test_karma_exports.py::test_self_export_log_story_happy tests/integration/test_karma_exports.py::test_self_export_stdio_t3_with_owned_content_returns_clean_jsonrpc -x

.PHONY: test-experts-s43-log
test-experts-s43-log:
	$(PYTHON) -m pytest tests/integration/test_karma_exports.py::test_self_export_log_story_happy -x

.PHONY: test-experts-s43-at
test-experts-s43-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S43 -x

.PHONY: test-experts-s43
test-experts-s43:
	+$(MAKE) test-experts-s43-backend
	+$(MAKE) test-experts-s43-at
	+$(MAKE) test-experts-s43-log

.PHONY: test-experts-s44-backend
test-experts-s44-backend:
	$(PYTHON) -m pytest tests/integration/test_karma_imports.py::test_import_service_t2_with_exported_files_generates_protocol_without_awards tests/integration/test_karma_imports.py::test_import_facade_t1_with_owned_draft_returns_protocol_without_awards tests/integration/test_karma_imports.py::test_import_legacy_registration_with_owned_draft_preserves_zero_awards tests/integration/test_karma_imports.py::test_import_facade_with_auto_apply_flag_preserves_existing_protocol_only_semantics tests/integration/test_karma_imports.py::test_import_stdio_t3_with_success_returns_clean_jsonrpc_without_awards tests/integration/test_karma_imports.py::test_import_with_missing_source_rejects_without_awards tests/integration/test_karma_imports.py::test_import_log_story_happy tests/integration/test_karma_imports.py::test_import_acceptance_with_exact_contract_runs_one_scenario -x

.PHONY: test-experts-s44-log
test-experts-s44-log:
	$(PYTHON) -m pytest tests/integration/test_karma_imports.py::test_import_log_story_happy -x

.PHONY: test-experts-s44-at
test-experts-s44-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S44 -x

.PHONY: test-experts-s44
test-experts-s44:
	+$(MAKE) test-experts-s44-backend
	+$(MAKE) test-experts-s44-at
	+$(MAKE) test-experts-s44-log

.PHONY: test-experts-s45-backend
test-experts-s45-backend:
	$(PYTHON) -m pytest tests/integration/karma_event/test_retry.py::test_record_event_with_repeated_write_preserves_original_event tests/integration/karma_event/test_retry.py::test_consumption_with_new_uuid_creates_new_complete_pair tests/integration/karma_event/test_retry.py::test_persist_awards_with_changed_payload_rejects_entire_batch tests/integration/karma_event/test_retry.py::test_event_with_outer_rollback_preserves_atomicity tests/integration/karma_event/test_retry.py::test_event_with_partial_existing_pair_rejects_without_repair tests/integration/karma_event/test_retry.py::test_event_with_concurrent_writers_preserves_one_complete_event tests/integration/karma_event/test_retry.py::test_event_with_database_constraints_rejects_changed_recipient tests/integration/karma_event/test_retry.py::test_first_release_with_historical_marker_preserves_singleton tests/integration/karma_event/test_retry.py::test_copy_receipt_with_retry_and_changed_target_enforces_identity tests/integration/karma_event/test_retry.py::test_karma_event_log_story_happy tests/integration/karma_event/test_retry.py::test_karma_event_log_story_reject -x

.PHONY: test-experts-s45-log
test-experts-s45-log:
	$(PYTHON) -m pytest tests/integration/karma_event/test_retry.py::test_karma_event_log_story_happy tests/integration/karma_event/test_retry.py::test_karma_event_log_story_reject -x

.PHONY: test-experts-s45-at
test-experts-s45-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S45 -x

.PHONY: test-experts-s45
test-experts-s45:
	+$(MAKE) test-experts-s45-backend
	+$(MAKE) test-experts-s45-at
	+$(MAKE) test-experts-s45-log

.PHONY: test-experts-s46-backend
test-experts-s46-backend:
	$(PYTHON) -m pytest tests/integration/karma_event/test_failures.py::test_consumption_with_denied_or_missing_target_preserves_global_ledger tests/integration/karma_event/test_failures.py::test_mcp_detail_with_denied_or_missing_target_preserves_global_ledger tests/integration/karma_event/test_failures.py::test_mcp_detail_with_invalid_token_preserves_global_ledger tests/integration/karma_event/test_failures.py::test_receipt_with_forged_fields_or_revoked_access_preserves_global_ledger tests/integration/karma_event/test_failures.py::test_export_with_real_filesystem_failure_preserves_global_ledger tests/integration/karma_event/test_failures.py::test_export_with_receipt_authentication_failure_preserves_completed_files tests/integration/karma_event/test_failures.py::test_mcp_stdio_with_denied_read_or_failed_export_returns_safe_error tests/integration/karma_event/test_failures.py::test_consumption_failure_log_story_reject tests/integration/karma_event/test_failures.py::test_consumption_receipt_failure_log_story_recovery -x

.PHONY: test-experts-s46-browser
test-experts-s46-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_karma_failures.py::test_copy_prompt_with_native_clipboard_denial_creates_no_receipt_or_awards -x

.PHONY: test-experts-s46-log
test-experts-s46-log:
	$(PYTHON) -m pytest tests/integration/karma_event/test_failures.py::test_consumption_failure_log_story_reject tests/integration/karma_event/test_failures.py::test_consumption_receipt_failure_log_story_recovery -x

.PHONY: test-experts-s46-at
test-experts-s46-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S46 -x

.PHONY: test-experts-s46
test-experts-s46:
	+$(MAKE) test-experts-s46-backend
	+$(MAKE) test-experts-s46-at
	+$(MAKE) test-experts-s46-browser
	+$(MAKE) test-experts-s46-log

.PHONY: test-experts-s47-backend
test-experts-s47-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_category_ties.py::test_primary_category_with_cedar_tie_expected_category tests/integration/test_experts_category_ties.py::test_primary_category_with_policy_boundaries_expected_category tests/integration/test_experts_category_ties.py::test_category_tie_loader_with_unknown_variant_rejects tests/integration/test_experts_category_ties.py::test_primary_category_with_cedar_ties_log_story_happy tests/integration/test_experts_category_acceptance.py::test_karma_category_acceptance_with_exact_outline_two_examples -x

.PHONY: test-experts-s47-browser
test-experts-s47-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_category_ties.py::test_primary_category_with_cedar_tie_renders_correct_tab -x

.PHONY: test-experts-s47-log
test-experts-s47-log:
	$(PYTHON) -m pytest tests/integration/test_experts_category_ties.py::test_primary_category_with_cedar_ties_log_story_happy -x

.PHONY: test-experts-s47-at
test-experts-s47-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S47 -x

.PHONY: test-experts-s47
test-experts-s47:
	+$(MAKE) test-experts-s47-backend
	+$(MAKE) test-experts-s47-at
	+$(MAKE) test-experts-s47-browser
	+$(MAKE) test-experts-s47-log

.PHONY: test-experts-s48-backend
test-experts-s48-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_sidebar_s48.py::test_sidebar_with_authenticated_elena_preserves_existing_navigation tests/integration/test_experts_sidebar_s48.py::test_sidebar_with_experts_destination_marks_only_experts_current tests/integration/test_experts_sidebar_s48.py::test_sidebar_log_story_happy tests/integration/test_experts_sidebar_s48.py::test_sidebar_acceptance_with_exact_contract_runs_one_passing_scenario -x

.PHONY: test-experts-s48-browser
test-experts-s48-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_sidebar_s48.py::test_sidebar_with_real_navigation_opens_experts -x

.PHONY: test-experts-s48-log
test-experts-s48-log:
	$(PYTHON) -m pytest tests/integration/test_experts_sidebar_s48.py::test_sidebar_log_story_happy -x

.PHONY: test-experts-s48-at
test-experts-s48-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S48 -x

.PHONY: test-experts-s48
test-experts-s48:
	+$(MAKE) test-experts-s48-backend
	+$(MAKE) test-experts-s48-at
	+$(MAKE) test-experts-s48-browser
	+$(MAKE) test-experts-s48-log

.PHONY: test-experts-s49-backend
test-experts-s49-backend:
	$(PYTHON) -m pytest tests/integration/test_experts_guest_navigation.py::test_guest_navigation_with_sidebar_href_reaches_public_experts -x

.PHONY: test-experts-s49-browser
test-experts-s49-browser:
	E2E_LIVE_SERVER_SCOPE=function $(PYTHON) -m pytest -c tests/e2e/pytest.ini -o addopts= -p no:playwright -p no:asyncio -p no:anyio tests/e2e/test_experts_guest_navigation.py::test_guest_navigation_with_real_sidebar_click_preserves_public_access -x

.PHONY: test-experts-s49-at
test-experts-s49-at:
	$(PYTHON) -m pytest tests/integration/test_experts_acceptance_runner.py -k S49 -x

.PHONY: test-experts-s49
test-experts-s49:
	+$(MAKE) test-experts-s49-backend
	+$(MAKE) test-experts-s49-at
	+$(MAKE) test-experts-s49-browser
