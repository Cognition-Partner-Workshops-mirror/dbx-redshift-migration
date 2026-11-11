.PHONY: deploy build reset verify dashboard-json verify-dashboard deploy-genie verify-genie
PROFILE ?= DEFAULT
TARGET ?= demo

deploy: verify-dashboard
	python deploy_app.py deploy --target $(TARGET) --profile $(PROFILE)

deploy-genie:
	DATABRICKS_CONFIG_PROFILE=$(PROFILE) python genie/manage.py deploy

verify-genie:
	DATABRICKS_CONFIG_PROFILE=$(PROFILE) python genie/verify_space.py

dashboard-json:
	python build_dashboard.py

verify-dashboard:
	DATABRICKS_CONFIG_PROFILE=$(PROFILE) python verify_dashboard.py

build:
	databricks bundle run customer_360_build -t $(TARGET) --profile $(PROFILE)

verify:
	DATABRICKS_CONFIG_PROFILE=$(PROFILE) python verify.py

reset:
	python deploy_app.py destroy --target $(TARGET) --profile $(PROFILE)
	DATABRICKS_CONFIG_PROFILE=$(PROFILE) python genie/manage.py delete
	DATABRICKS_CONFIG_PROFILE=$(PROFILE) python reset.py
