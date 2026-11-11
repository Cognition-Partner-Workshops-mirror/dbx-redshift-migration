.PHONY: deploy build verify test genie app-deploy app-grants all

TARGET ?= demo_redshift
PYTHON ?= python
export DATABRICKS_CONFIG_PROFILE ?= DEFAULT

deploy:
	databricks bundle deploy -t $(TARGET)

build:
	databricks bundle run -t $(TARGET) customer_360_build

verify:
	$(PYTHON) verify.py

genie:
	$(PYTHON) genie/manage.py

app-deploy:
	databricks bundle run -t $(TARGET) customer_lookup

test:
	$(PYTHON) -m pytest -q tests

all: deploy build verify genie app-grants app-deploy

app-grants:
	SP=$$(databricks apps get customer-lookup -o json | $(PYTHON) -c "import sys,json;print(json.load(sys.stdin)['service_principal_client_id'])") && \
	databricks api post /api/2.0/sql/statements --json "{\"warehouse_id\":\"6dc4b80538621b7b\",\"statement\":\"GRANT USE CATALOG ON CATALOG demo_redshift TO \`$$SP\`\",\"wait_timeout\":\"30s\"}" >/dev/null && \
	databricks api post /api/2.0/sql/statements --json "{\"warehouse_id\":\"6dc4b80538621b7b\",\"statement\":\"GRANT USE SCHEMA, SELECT ON SCHEMA demo_redshift.customer_360 TO \`$$SP\`\",\"wait_timeout\":\"30s\"}" >/dev/null
