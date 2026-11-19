PROFILE ?= DEFAULT
WAREHOUSE ?= 6dc4b80538621b7b
WAREHOUSE_ADMIN_PROFILE ?= devin-admin
PYTHON ?= python3

.PHONY: deploy build verify test dashboard-check dashboard genie genie-check app
deploy:
	BUNDLE_VAR_warehouse_id=$(WAREHOUSE) databricks bundle validate --strict --profile $(PROFILE)
	BUNDLE_VAR_warehouse_id=$(WAREHOUSE) databricks bundle deploy --select jobs.build --profile $(PROFILE)

build:
	BUNDLE_VAR_warehouse_id=$(WAREHOUSE) databricks bundle run build --profile $(PROFILE)

verify:
	DATABRICKS_CONFIG_PROFILE=$(PROFILE) $(PYTHON) verify.py --warehouse $(WAREHOUSE)

test:
	$(PYTHON) -m pytest -q tests

dashboard-check:
	DATABRICKS_CONFIG_PROFILE=$(PROFILE) $(PYTHON) verify.py --warehouse $(WAREHOUSE) --dashboard

dashboard: dashboard-check
	BUNDLE_VAR_warehouse_id=$(WAREHOUSE) databricks bundle deploy --select dashboards.customer_health --profile $(PROFILE)

genie:
	DATABRICKS_CONFIG_PROFILE=$(PROFILE) $(PYTHON) genie/manage.py --warehouse $(WAREHOUSE)

genie-check:
	DATABRICKS_CONFIG_PROFILE=$(PROFILE) $(PYTHON) genie/manage.py --warehouse $(WAREHOUSE) --verify

app:
	@set -e; \
	    export DATABRICKS_CONFIG_PROFILE=$(PROFILE) BUNDLE_VAR_warehouse_id=$(WAREHOUSE); \
	    BUNDLE_VAR_genie_space_id=$$($(PYTHON) genie/manage.py --warehouse $(WAREHOUSE) --id); \
	    export BUNDLE_VAR_genie_space_id; \
	    databricks bundle validate --strict; \
	    databricks bundle deploy --select apps.customer_lookup; \
	    $(PYTHON) app_access.py --warehouse $(WAREHOUSE) --warehouse-admin-profile $(WAREHOUSE_ADMIN_PROFILE) \
	        --genie-space "$$BUNDLE_VAR_genie_space_id"; \
	    databricks bundle run customer_lookup
